import os
import logging
import threading
import time
from datetime import datetime
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import jwt_required
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Import custom modules
from detector import VehicleDetector
from stream_processor import RTSPStreamProcessor
from bay_tracker import BayTracker, BayStatus
from auth import init_jwt, register_auth_routes
from admin_dashboard import init_admin_dashboard

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('app')

# RTSP stream URLs
RTSP_URLS = {
    1: os.environ.get('RTSP_URL_1', 'rtsp://192.168.1.74:7447/VJ1fB8D4d03nIwKF'),
    2: os.environ.get('RTSP_URL_2', 'rtsp://192.168.1.74:7447/zfDlcWJLTq10A49M'),
    3: os.environ.get('RTSP_URL_3', 'rtsp://192.168.1.74:7447/18JUhav6VfoOMVS0'),
    4: os.environ.get('RTSP_URL_4', 'rtsp://192.168.1.74:7447/BSPtMFwAXLncNdx0')
}

# YOLOv4 model paths
YOLO_CONFIG_PATH = os.environ.get('YOLO_CONFIG_PATH', 'yolov4/yolov4-csp.cfg')
YOLO_WEIGHTS_PATH = os.environ.get('YOLO_WEIGHTS_PATH', 'yolov4/yolov4-csp.weights')
YOLO_NAMES_PATH = os.environ.get('YOLO_NAMES_PATH', 'backend/coco.names')

# Detection parameters
CONFIDENCE_THRESHOLD = float(os.environ.get('CONFIDENCE_THRESHOLD', '0.5'))
NMS_THRESHOLD = float(os.environ.get('NMS_THRESHOLD', '0.4'))
STATUS_CHANGE_THRESHOLD = int(os.environ.get('STATUS_CHANGE_THRESHOLD', '3'))

# Create Flask app
app = Flask(__name__)
CORS(app)

# Configure app
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['SESSION_TYPE'] = 'filesystem'

# Initialize JWT
jwt = init_jwt(app)

# Register authentication routes
register_auth_routes(app)

# Global objects
detector = None
bay_tracker = None
stream_processors = {}
start_time = datetime.now()

def initialize_system():
    """
    Initialize the vehicle detection system.
    """
    global detector, bay_tracker, stream_processors
    
    try:
        # Initialize vehicle detector
        logger.info("Initializing vehicle detector...")
        detector = VehicleDetector(
            YOLO_CONFIG_PATH,
            YOLO_WEIGHTS_PATH,
            YOLO_NAMES_PATH,
            CONFIDENCE_THRESHOLD,
            NMS_THRESHOLD
        )
        
        # Initialize bay tracker
        logger.info("Initializing bay tracker...")
        bay_tracker = BayTracker(
            bay_count=len(RTSP_URLS),
            status_change_threshold=STATUS_CHANGE_THRESHOLD
        )
        
        # Initialize stream processors
        logger.info("Initializing stream processors...")
        for bay_id, rtsp_url in RTSP_URLS.items():
            stream_processors[bay_id] = RTSPStreamProcessor(
                bay_id=bay_id,
                rtsp_url=rtsp_url,
                detector=detector
            )
        
        # Initialize admin dashboard
        logger.info("Initializing admin dashboard...")
        init_admin_dashboard(app, bay_tracker, stream_processors)
        
        logger.info("System initialization complete")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing system: {str(e)}")
        return False

def start_stream_processors():
    """
    Start all stream processors.
    """
    logger.info("Starting stream processors...")
    
    for bay_id, processor in stream_processors.items():
        try:
            processor.start()
            logger.info(f"Started stream processor for Bay {bay_id}")
        except Exception as e:
            logger.error(f"Error starting stream processor for Bay {bay_id}: {str(e)}")

def stop_stream_processors():
    """
    Stop all stream processors.
    """
    logger.info("Stopping stream processors...")
    
    for bay_id, processor in stream_processors.items():
        try:
            processor.stop()
            logger.info(f"Stopped stream processor for Bay {bay_id}")
        except Exception as e:
            logger.error(f"Error stopping stream processor for Bay {bay_id}: {str(e)}")

def update_bay_statuses():
    """
    Update bay statuses based on stream processor results.
    """
    while True:
        try:
            for bay_id, processor in stream_processors.items():
                status = processor.get_status()
                
                bay_tracker.update_bay_status(
                    bay_id=bay_id,
                    vehicle_detected=status['vehicle_detected'],
                    is_connected=status['is_connected'],
                    last_frame_time=status['last_frame_time'],
                    detection_confidence=status['detection_confidence']
                )
            
            # Sleep to control update rate
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Error updating bay statuses: {str(e)}")
            time.sleep(5)  # Wait longer on error

# API routes
@app.route('/api/stations', methods=['GET'])
@jwt_required()
def get_stations():
    """
    Get the status of all stations (authenticated).
    """
    try:
        return _get_station_statuses()
    except Exception as e:
        logger.error(f"Error getting stations: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/guest/stations', methods=['GET'])
def get_stations_guest():
    """
    Get the status of all stations (guest mode, no authentication required).
    """
    try:
        return _get_station_statuses()
    except Exception as e:
        logger.error(f"Error getting stations for guest: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

def _get_station_statuses():
    """
    Helper function to get station statuses.
    """
    # Get bay statuses
    bay_statuses = bay_tracker.get_all_bay_statuses()
    
    # Convert to format expected by Flutter app
    stations = []
    for bay in bay_statuses:
        # Skip bays with connection errors for the app
        if bay['status'] == 'connectionError':
            status = 'outOfService'  # Map connection errors to out of service for the app
        else:
            status = bay['status']
        
        stations.append({
            'id': bay['id'],
            'status': status,
            'lastUpdated': bay['lastUpdated']
        })
    
    return jsonify(stations)

@app.route('/api/health', methods=['GET'])
def health_check():
    """
    Health check endpoint.
    """
    uptime = (datetime.now() - start_time).total_seconds()
    
    return jsonify({
        'status': 'ok',
        'uptime': uptime,
        'version': '1.0.0'
    })

# Main entry point
if __name__ == '__main__':
    # Initialize system
    if not initialize_system():
        logger.error("Failed to initialize system, exiting")
        exit(1)
    
    # Start stream processors
    start_stream_processors()
    
    # Start bay status update thread
    update_thread = threading.Thread(target=update_bay_statuses)
    update_thread.daemon = True
    update_thread.start()
    
    try:
        # Start Flask app
        port = int(os.environ.get('PORT', 5000))
        logger.info(f"Starting Flask app on port {port}")
        app.run(host='0.0.0.0', port=port, debug=False)
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down")
    
    finally:
        # Stop stream processors
        stop_stream_processors()
        logger.info("Application shutdown complete")
