#!/usr/bin/env python3
"""
Script to run the car wash backend server.
"""
import os
import sys
import subprocess
import argparse

def check_requirements():
    """Check if all required packages are installed."""
    try:
        import flask
        import flask_cors
        import flask_jwt_extended
        import numpy
        import cv2
        import dotenv
        return True
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Please install all required packages: pip install -r requirements.txt")
        return False

def check_model_files():
    """Check if YOLOv4 model files exist."""
    model_files = [
        "../yolov4/yolov4-csp.cfg",
        "../yolov4/yolov4-csp.weights",
        "coco.names"
    ]
    
    missing_files = []
    for file_path in model_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print("Missing model files:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        return False
    
    return True

def run_server(debug=False, host="0.0.0.0", port=5000):
    """Run the Flask server."""
    # Set environment variables
    env = os.environ.copy()
    if debug:
        env["FLASK_ENV"] = "development"
        env["FLASK_DEBUG"] = "1"
    
    env["PORT"] = str(port)
    
    # Run the server
    cmd = [sys.executable, "app.py"]
    print(f"Starting server on {host}:{port}...")
    
    try:
        subprocess.run(cmd, env=env, check=True)
    except KeyboardInterrupt:
        print("\nServer stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"Server error: {e}")
        return 1
    
    return 0

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Run the car wash backend server")
    parser.add_argument("--debug", action="store_true", help="Run in debug mode")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=5000, help="Port to bind to")
    parser.add_argument("--skip-checks", action="store_true", help="Skip dependency and model checks")
    
    args = parser.parse_args()
    
    # Change to the script's directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    if not args.skip_checks:
        # Check requirements
        if not check_requirements():
            return 1
        
        # Check model files
        if not check_model_files():
            return 1
    
    # Run the server
    return run_server(args.debug, args.host, args.port)

if __name__ == "__main__":
    sys.exit(main())
