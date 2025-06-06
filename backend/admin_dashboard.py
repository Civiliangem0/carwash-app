import logging
import os
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, request, session, flash

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('admin_dashboard')

# Admin credentials (in a real app, these would be in a secure database)
ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD', 'admin')

# Create blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def login_required(f):
    """
    Decorator to require admin login for routes.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            return redirect(url_for('admin.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Admin login page.
    """
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['admin_logged_in'] = True
            logger.info(f"Admin login successful: {username}")
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Invalid username or password')
            logger.warning(f"Failed admin login attempt: {username}")
    
    return render_template('admin_login.html')

@admin_bp.route('/logout')
def logout():
    """
    Admin logout.
    """
    session.pop('admin_logged_in', None)
    return redirect(url_for('admin.login'))

@admin_bp.route('/')
@login_required
def dashboard():
    """
    Admin dashboard page.
    """
    return render_template('dashboard.html')

def init_admin_dashboard(app, bay_tracker, stream_processors):
    """
    Initialize the admin dashboard.
    
    Args:
        app: Flask application instance
        bay_tracker: BayTracker instance
        stream_processors: Dictionary of RTSPStreamProcessor instances
    """
    # Create templates directory if it doesn't exist
    templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
    os.makedirs(templates_dir, exist_ok=True)
    
    # Create admin login template
    admin_login_path = os.path.join(templates_dir, 'admin_login.html')
    if not os.path.exists(admin_login_path):
        with open(admin_login_path, 'w') as f:
            f.write("""<!DOCTYPE html>
<html>
<head>
    <title>Admin Login</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f5f5f5;
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
        }
        .login-container {
            background-color: white;
            padding: 2rem;
            border-radius: 8px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            width: 100%;
            max-width: 400px;
        }
        h1 {
            text-align: center;
            color: #333;
            margin-bottom: 1.5rem;
        }
        .form-group {
            margin-bottom: 1rem;
        }
        label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: bold;
        }
        input[type="text"],
        input[type="password"] {
            width: 100%;
            padding: 0.75rem;
            border: 1px solid #ddd;
            border-radius: 4px;
            font-size: 1rem;
        }
        button {
            background-color: #4CAF50;
            color: white;
            border: none;
            padding: 0.75rem 1rem;
            border-radius: 4px;
            cursor: pointer;
            font-size: 1rem;
            width: 100%;
            margin-top: 1rem;
        }
        button:hover {
            background-color: #45a049;
        }
        .flash-message {
            background-color: #f8d7da;
            color: #721c24;
            padding: 0.75rem;
            border-radius: 4px;
            margin-bottom: 1rem;
        }
    </style>
</head>
<body>
    <div class="login-container">
        <h1>Admin Login</h1>
        
        {% if get_flashed_messages() %}
        <div class="flash-message">
            {{ get_flashed_messages()[0] }}
        </div>
        {% endif %}
        
        <form method="post">
            <div class="form-group">
                <label for="username">Username</label>
                <input type="text" id="username" name="username" required>
            </div>
            
            <div class="form-group">
                <label for="password">Password</label>
                <input type="password" id="password" name="password" required>
            </div>
            
            <button type="submit">Login</button>
        </form>
    </div>
</body>
</html>""")
    
    # Create dashboard template
    dashboard_path = os.path.join(templates_dir, 'dashboard.html')
    if not os.path.exists(dashboard_path):
        with open(dashboard_path, 'w') as f:
            f.write("""<!DOCTYPE html>
<html>
<head>
    <title>Car Wash Admin Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: Arial, sans-serif;
            background-color: #f5f5f5;
            margin: 0;
            padding: 0;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 1rem;
        }
        header {
            background-color: #333;
            color: white;
            padding: 1rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        h1 {
            margin: 0;
        }
        .logout-btn {
            background-color: #d9534f;
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            cursor: pointer;
            text-decoration: none;
        }
        .bay-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
            gap: 1rem;
            margin-top: 1rem;
        }
        .bay-card {
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            padding: 1rem;
        }
        .bay-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 0.5rem;
        }
        .bay-title {
            font-size: 1.25rem;
            font-weight: bold;
            margin: 0;
        }
        .status-badge {
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.875rem;
            font-weight: bold;
        }
        .status-available {
            background-color: #d4edda;
            color: #155724;
        }
        .status-in-use {
            background-color: #f8d7da;
            color: #721c24;
        }
        .status-out-of-service {
            background-color: #fff3cd;
            color: #856404;
        }
        .status-error {
            background-color: #cce5ff;
            color: #004085;
        }
        .bay-details {
            margin-top: 1rem;
            font-size: 0.875rem;
        }
        .detail-row {
            display: flex;
            justify-content: space-between;
            margin-bottom: 0.5rem;
        }
        .detail-label {
            color: #666;
        }
        .system-info {
            background-color: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
            padding: 1rem;
            margin-top: 1rem;
        }
        .refresh-container {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 1rem;
        }
        .refresh-btn {
            background-color: #007bff;
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            cursor: pointer;
        }
        .last-updated {
            font-size: 0.875rem;
            color: #666;
        }
    </style>
</head>
<body>
    <header>
        <h1>Car Wash Admin Dashboard</h1>
        <a href="/admin/logout" class="logout-btn">Logout</a>
    </header>
    
    <div class="container">
        <div class="refresh-container">
            <button id="refresh-btn" class="refresh-btn">Refresh Data</button>
            <span class="last-updated" id="last-updated">Last updated: Just now</span>
        </div>
        
        <div class="bay-grid" id="bay-grid">
            <!-- Bay cards will be inserted here by JavaScript -->
        </div>
        
        <div class="system-info">
            <h2>System Information</h2>
            <div class="detail-row">
                <span class="detail-label">Server Status:</span>
                <span id="server-status">Running</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">Uptime:</span>
                <span id="uptime">0 minutes</span>
            </div>
        </div>
    </div>
    
    <script>
        // Start time for uptime calculation
        const startTime = new Date();
        
        // Function to format date
        function formatDate(date) {
            return date.toLocaleTimeString();
        }
        
        // Function to update uptime
        function updateUptime() {
            const now = new Date();
            const diff = Math.floor((now - startTime) / 1000 / 60);
            document.getElementById('uptime').textContent = `${diff} minutes`;
        }
        
        // Function to get status class
        function getStatusClass(status) {
            switch(status) {
                case 'available':
                    return 'status-available';
                case 'inUse':
                    return 'status-in-use';
                case 'outOfService':
                    return 'status-out-of-service';
                case 'connectionError':
                    return 'status-error';
                default:
                    return '';
            }
        }
        
        // Function to get status text
        function getStatusText(status) {
            switch(status) {
                case 'available':
                    return 'Available';
                case 'inUse':
                    return 'In Use';
                case 'outOfService':
                    return 'Out of Service';
                case 'connectionError':
                    return 'Connection Error';
                default:
                    return status;
            }
        }
        
        // Function to fetch bay data
        async function fetchBayData() {
            try {
                const response = await fetch('/api/admin/bays');
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const data = await response.json();
                return data;
            } catch (error) {
                console.error('Error fetching bay data:', error);
                return [];
            }
        }
        
        // Function to update bay grid
        async function updateBayGrid() {
            const bayGrid = document.getElementById('bay-grid');
            const bays = await fetchBayData();
            
            // Clear existing content
            bayGrid.innerHTML = '';
            
            // Add bay cards
            bays.forEach(bay => {
                const bayCard = document.createElement('div');
                bayCard.className = 'bay-card';
                
                const lastUpdated = new Date(bay.lastUpdated);
                
                bayCard.innerHTML = `
                    <div class="bay-header">
                        <h2 class="bay-title">Bay ${bay.id}</h2>
                        <span class="status-badge ${getStatusClass(bay.status)}">${getStatusText(bay.status)}</span>
                    </div>
                    <div class="bay-details">
                        <div class="detail-row">
                            <span class="detail-label">Connection:</span>
                            <span>${bay.isConnected ? 'Connected' : 'Disconnected'}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Last Updated:</span>
                            <span>${formatDate(lastUpdated)}</span>
                        </div>
                        <div class="detail-row">
                            <span class="detail-label">Detection Confidence:</span>
                            <span>${(bay.detectionConfidence * 100).toFixed(1)}%</span>
                        </div>
                    </div>
                `;
                
                bayGrid.appendChild(bayCard);
            });
            
            // Update last updated time
            document.getElementById('last-updated').textContent = `Last updated: ${formatDate(new Date())}`;
        }
        
        // Initial update
        updateBayGrid();
        
        // Set up refresh button
        document.getElementById('refresh-btn').addEventListener('click', updateBayGrid);
        
        // Set up auto-refresh every 5 seconds
        setInterval(updateBayGrid, 5000);
        
        // Update uptime every minute
        setInterval(updateUptime, 60000);
        updateUptime();
    </script>
</body>
</html>""")
    
    # Register blueprint with app
    app.register_blueprint(admin_bp)
    
    # Add admin API routes
    @app.route('/api/admin/bays')
    @login_required
    def admin_bays():
        """
        API endpoint for getting bay statuses for admin dashboard.
        """
        bay_statuses = bay_tracker.get_all_bay_statuses()
        
        # Add additional information for admin
        for bay in bay_statuses:
            bay_id = bay['id']
            if bay_id in stream_processors:
                processor = stream_processors[bay_id]
                processor_status = processor.get_status()
                
                # Add processor status details
                bay['isConnected'] = processor_status['is_connected']
                bay['detectionConfidence'] = processor_status['detection_confidence']
                bay['reconnectAttempts'] = processor_status['reconnect_attempts']
                
                # Add last frame time if available
                if processor_status['last_frame_time']:
                    bay['lastFrameTime'] = processor_status['last_frame_time'].isoformat()
        
        return bay_statuses
    
    logger.info("Admin dashboard initialized")
