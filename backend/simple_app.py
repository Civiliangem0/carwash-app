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
from simple_stream_processor import SimpleRTSPStreamProcessor
from bay_tracker import BayTracker, BayStatus
from auth import init_jwt, register_auth_routes
from admin_dashboard import init_admin_dashboard
from config import get_config, reload_config
from health_monitor import get_health_monitor

# Configure logging - Info level for production
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('simple_app')

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
bay_tracker = None
stream_processors = {}
health_monitor = None
start_time = datetime.now()

def initialize_system():
    """Initialize the advanced car detection system."""
    global bay_tracker, stream_processors, health_monitor
    
    try:
        logger.info("🚀 Initializing ADVANCED car detection system...")
        
        # Load configuration
        config = get_config()
        logger.info(f"Configuration loaded: {config.bay_count} bays, "
                   f"thresholds: {config.status.available_to_inuse_threshold}→{config.status.inuse_to_available_threshold}")
        
        # Initialize bay tracker with configuration
        logger.info("Initializing advanced bay tracker...")
        bay_tracker = BayTracker()
        
        # Initialize health monitor
        logger.info("Initializing health monitor...")
        health_monitor = get_health_monitor()
        
        # Initialize stream processors with configuration
        logger.info("Initializing advanced stream processors...")
        for bay_id, rtsp_url in config.rtsp_urls.items():
            logger.info(f"Creating advanced detector for Bay {bay_id}...")
            
            stream_processors[bay_id] = SimpleRTSPStreamProcessor(
                bay_id=bay_id,
                rtsp_url=rtsp_url
            )
        
        # Initialize admin dashboard
        logger.info("Initializing admin dashboard...")
        init_admin_dashboard(app, bay_tracker, stream_processors)
        
        logger.info("✅ Advanced system initialization complete!")
        logger.info("🎯 Features: Asymmetric transitions, Auto-recovery, Health monitoring, Quality adaptation")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing system: {str(e)}")
        return False

def start_stream_processors():
    """Start all stream processors."""
    logger.info("Starting simple stream processors...")
    
    for bay_id, processor in stream_processors.items():
        try:
            processor.start()
            logger.info(f"Started simple stream processor for Bay {bay_id}")
        except Exception as e:
            logger.error(f"Error starting stream processor for Bay {bay_id}: {str(e)}")

def stop_stream_processors():
    """Stop all stream processors."""
    logger.info("Stopping stream processors...")
    
    for bay_id, processor in stream_processors.items():
        try:
            processor.stop()
            logger.info(f"Stopped stream processor for Bay {bay_id}")
        except Exception as e:
            logger.error(f"Error stopping stream processor for Bay {bay_id}: {str(e)}")

def update_bay_statuses():
    """Update bay statuses based on simple stream processor results."""
    last_status_log = 0
    while True:
        try:
            for bay_id, processor in stream_processors.items():
                status = processor.get_status()
                
                # Debug logging to understand status updates
                if status['vehicle_detected']:
                    logger.debug(f"Updating Bay {bay_id}: vehicle_detected=True, connected={status['is_connected']}, conf={status['detection_confidence']:.2f}")
                
                bay_tracker.update_bay_status(
                    bay_id=bay_id,
                    vehicle_detected=status['vehicle_detected'],
                    is_connected=status['is_connected'],
                    last_frame_time=status['last_frame_time'],
                    detection_confidence=status['detection_confidence']
                )
            
            # Update health monitor
            if health_monitor:
                for bay_id, processor in stream_processors.items():
                    status = processor.get_status()
                    health_monitor.update_bay_health(bay_id, status)
            
            # Log bay status summary periodically
            current_time = time.time()
            config = get_config()
            if current_time - last_status_log >= config.status_log_interval:
                status_summary = []
                for bay_id in range(1, config.bay_count + 1):
                    bay_status = bay_tracker.get_bay_status(bay_id)
                    if bay_status:
                        if bay_status['status'] == 'inUse':
                            emoji = "🚗"
                        elif bay_status['status'] == 'connectionError':
                            emoji = "❌"
                        else:
                            emoji = "🅿️"
                        status_summary.append(f"Bay {bay_id}: {emoji} {bay_status['status']}")
                
                logger.info(f"🏪 BAY STATUS: {' | '.join(status_summary)}")
                last_status_log = current_time
            
            # Sleep to control update rate
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"Error updating bay statuses: {str(e)}")
            time.sleep(5)  # Wait longer on error

# API routes (same as before)
@app.route('/api/stations', methods=['GET'])
@jwt_required()
def get_stations():
    """Get the status of all stations (authenticated)."""
    try:
        return _get_station_statuses()
    except Exception as e:
        logger.error(f"Error getting stations: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/guest/stations', methods=['GET'])
def get_stations_guest():
    """Get the status of all stations (guest mode, no authentication required)."""
    try:
        return _get_station_statuses()
    except Exception as e:
        logger.error(f"Error getting stations for guest: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

def _get_station_statuses():
    """Helper function to get station statuses."""
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
    """Health check endpoint."""
    uptime = (datetime.now() - start_time).total_seconds()
    
    return jsonify({
        'status': 'ok',
        'uptime': uptime,
        'version': '2.0.0-simple',
        'detection_method': 'background_subtraction'
    })

@app.route('/api/reset_background/<int:bay_id>', methods=['POST'])
def reset_background(bay_id):
    """Reset background model for a specific bay (admin feature)."""
    if bay_id in stream_processors:
        stream_processors[bay_id].reset_background()
        logger.info(f"🔄 Manual background reset for Bay {bay_id}")
        return jsonify({'message': f'Background reset for Bay {bay_id}'})
    else:
        return jsonify({'error': 'Invalid bay ID'}), 400

@app.route('/api/bay/<int:bay_id>/force_available', methods=['POST'])
def force_bay_available(bay_id):
    """Force a bay to available status (manual override)."""
    if bay_id in stream_processors and bay_tracker:
        # Reset bay status
        bay_tracker.set_bay_out_of_service(bay_id, False)  # Set to available
        
        # Reset background to help with detection
        stream_processors[bay_id].reset_background()
        
        logger.info(f"🔧 Manual override: Bay {bay_id} forced to available")
        return jsonify({'message': f'Bay {bay_id} forced to available status'})
    else:
        return jsonify({'error': 'Invalid bay ID'}), 400

@app.route('/api/health', methods=['GET'])
def get_health():
    """Get comprehensive system health information."""
    try:
        if health_monitor:
            health_summary = health_monitor.get_health_summary()
            return jsonify(health_summary)
        else:
            return jsonify({'error': 'Health monitor not available'}), 503
    except Exception as e:
        logger.error(f"Error getting health info: {str(e)}")
        return jsonify({'error': 'Health check failed'}), 500

@app.route('/api/config', methods=['GET'])
def get_config_api():
    """Get current system configuration."""
    try:
        config = get_config()
        return jsonify({
            'detection': {
                'learning_rate': config.detection.learning_rate,
                'min_contour_area': config.detection.min_contour_area,
                'bay_center_ratio': config.detection.bay_center_ratio,
                'confidence_threshold': config.detection.confidence_threshold
            },
            'status': {
                'available_to_inuse_threshold': config.status.available_to_inuse_threshold,
                'inuse_to_available_threshold': config.status.inuse_to_available_threshold,
                'connection_grace_period': config.status.connection_grace_period
            },
            'rtsp': {
                'max_reconnect_attempts': config.rtsp.max_reconnect_attempts,
                'base_reconnect_interval': config.rtsp.base_reconnect_interval,
                'target_fps': config.rtsp.target_fps
            }
        })
    except Exception as e:
        logger.error(f"Error getting config: {str(e)}")
        return jsonify({'error': 'Config retrieval failed'}), 500

@app.route('/api/config/reload', methods=['POST'])
def reload_config_api():
    """Reload configuration from environment variables."""
    try:
        new_config = reload_config()
        logger.info("📝 Configuration reloaded from environment variables")
        return jsonify({'message': 'Configuration reloaded successfully'})
    except Exception as e:
        logger.error(f"Error reloading config: {str(e)}")
        return jsonify({'error': 'Config reload failed'}), 500

# Main entry point
if __name__ == '__main__':
    logger.info("🎯 Starting SIMPLE Car Wash Detection System")
    logger.info("🚫 NO YOLOv4 - Using background subtraction instead!")
    
    # Initialize system
    if not initialize_system():
        logger.error("Failed to initialize system, exiting")
        exit(1)
    
    # Start stream processors
    start_stream_processors()
    
    # Start health monitoring
    if health_monitor:
        health_monitor.start_monitoring()
    
    # Start bay status update thread
    update_thread = threading.Thread(target=update_bay_statuses)
    update_thread.daemon = True
    update_thread.start()
    
    try:
        # Start Flask app
        port = int(os.environ.get('PORT', 5000))
        logger.info(f"🌐 Starting Flask app on port {port}")
        app.run(host='0.0.0.0', port=port, debug=False)
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt, shutting down")
    
    finally:
        # Stop health monitoring
        if health_monitor:
            health_monitor.stop_monitoring()
        
        # Stop stream processors
        stop_stream_processors()
        logger.info("Application shutdown complete")