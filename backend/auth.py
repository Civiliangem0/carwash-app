import logging
import os
import json
from datetime import datetime, timedelta
from functools import wraps
from flask import request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token, get_jwt_identity, verify_jwt_in_request,
    JWTManager, jwt_required
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('auth')

# User database file
USERS_FILE = os.path.join(os.path.dirname(__file__), 'users.json')

def init_jwt(app):
    """
    Initialize JWT authentication for the Flask app.
    
    Args:
        app: Flask application instance
    """
    # Configure JWT
    app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'dev-secret-key')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(days=30)
    
    # Initialize JWT manager
    jwt = JWTManager(app)
    
    # Create users file if it doesn't exist
    if not os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'w') as f:
            json.dump([], f)
        logger.info(f"Created empty users file at {USERS_FILE}")
    
    logger.info("JWT authentication initialized")
    
    return jwt

def get_users():
    """
    Get all users from the users file.
    
    Returns:
        list: List of user dictionaries
    """
    try:
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        logger.error(f"Error reading users file: {USERS_FILE}")
        return []

def save_users(users):
    """
    Save users to the users file.
    
    Args:
        users: List of user dictionaries
    """
    try:
        with open(USERS_FILE, 'w') as f:
            json.dump(users, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving users file: {str(e)}")

def find_user(username):
    """
    Find a user by username.
    
    Args:
        username: Username to find
        
    Returns:
        dict: User dictionary or None if not found
    """
    users = get_users()
    for user in users:
        if user['username'] == username:
            return user
    return None

def register_user(username, password, is_admin=False):
    """
    Register a new user.
    
    Args:
        username: Username for the new user
        password: Password for the new user
        is_admin: Boolean indicating if the user is an admin
        
    Returns:
        tuple: (success, message)
    """
    # Check if username already exists
    if find_user(username):
        return False, "Username already exists"
    
    # Get existing users
    users = get_users()
    
    # Add new user
    users.append({
        'username': username,
        'password': password,  # In a real app, this should be hashed
        'is_admin': is_admin,
        'created_at': datetime.now().isoformat()
    })
    
    # Save users
    save_users(users)
    
    logger.info(f"Registered new user: {username}")
    return True, "User registered successfully"

def authenticate_user(username, password):
    """
    Authenticate a user.
    
    Args:
        username: Username to authenticate
        password: Password to authenticate
        
    Returns:
        tuple: (success, user or error message)
    """
    user = find_user(username)
    
    if not user:
        return False, "User not found"
    
    if user['password'] != password:  # In a real app, compare hashed passwords
        return False, "Invalid password"
    
    return True, user

def admin_required(fn):
    """
    Decorator to require admin privileges for a route.
    
    Args:
        fn: Function to decorate
        
    Returns:
        function: Decorated function
    """
    @wraps(fn)
    def wrapper(*args, **kwargs):
        # Verify JWT is valid
        verify_jwt_in_request()
        
        # Get current user
        username = get_jwt_identity()
        user = find_user(username)
        
        # Check if user is admin
        if not user or not user.get('is_admin', False):
            return jsonify({"msg": "Admin privileges required"}), 403
        
        # Call original function
        return fn(*args, **kwargs)
    
    return wrapper

# API route handlers
def register_auth_routes(app):
    """
    Register authentication routes with the Flask app.
    
    Args:
        app: Flask application instance
    """
    @app.route('/api/auth/register', methods=['POST'])
    def register():
        """
        Register a new user.
        """
        data = request.get_json()
        
        # Validate input
        if not data or not data.get('username') or not data.get('password'):
            return jsonify({"msg": "Username and password required"}), 400
        
        # Register user
        success, message = register_user(
            data['username'], 
            data['password'],
            data.get('is_admin', False)
        )
        
        if not success:
            return jsonify({"msg": message}), 400
        
        return jsonify({"msg": message}), 201
    
    @app.route('/api/auth/login', methods=['POST'])
    def login():
        """
        Authenticate a user and issue a JWT token.
        """
        data = request.get_json()
        
        # Validate input
        if not data or not data.get('username') or not data.get('password'):
            return jsonify({"msg": "Username and password required"}), 400
        
        # Authenticate user
        success, result = authenticate_user(data['username'], data['password'])
        
        if not success:
            return jsonify({"msg": result}), 401
        
        # Create access token
        access_token = create_access_token(identity=data['username'])
        
        return jsonify({
            "access_token": access_token,
            "username": data['username'],
            "is_admin": result.get('is_admin', False)
        }), 200
    
    logger.info("Authentication routes registered")
