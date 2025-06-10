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
        background_status = []
        for bay_id, rtsp_url in config.rtsp_urls.items():
            logger.info(f"Creating advanced detector for Bay {bay_id}...")
            
            processor = SimpleRTSPStreamProcessor(
                bay_id=bay_id,
                rtsp_url=rtsp_url
            )
            stream_processors[bay_id] = processor
            
            # Check if background was loaded
            if processor.detector.background_loaded:
                background_status.append(f"Bay {bay_id}: ⚡ Instant")
            else:
                background_status.append(f"Bay {bay_id}: 🔄 Learning")
        
        # Log background loading summary
        logger.info(f"🎯 Background Status: {' | '.join(background_status)}")
        
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
    logger.info("🔄 Bay status update thread starting...")
    last_status_log = 0
    loop_count = 0
    last_health_log = time.time()
    
    while True:
        try:
            loop_count += 1
            
            # Log first loop to confirm thread is working
            if loop_count == 1:
                logger.info("🔄 Bay status thread: First loop iteration starting...")
            
            # Thread health check - log every 30 seconds to confirm thread is alive
            current_time = time.time()
            if current_time - last_health_log >= 30:
                logger.info(f"💓 Bay status thread health check - Loop #{loop_count}, running for {current_time - last_health_log:.0f}s")
                last_health_log = current_time
            
            # Collect statuses with timeout protection and detailed logging
            logger.debug(f"🔄 Loop #{loop_count}: Starting status collection from {len(stream_processors)} processors")
            statuses = {}
            
            for bay_id, processor in stream_processors.items():
                try:
                    logger.debug(f"🔄 Loop #{loop_count}: Getting status from Bay {bay_id} processor")
                    
                    # Use a timeout mechanism to prevent hanging
                    import signal
                    
                    def timeout_handler(signum, frame):
                        raise TimeoutError(f"Timeout getting status from Bay {bay_id}")
                    
                    # Set timeout (only on Unix systems)
                    if hasattr(signal, 'SIGALRM'):
                        signal.signal(signal.SIGALRM, timeout_handler)
                        signal.alarm(5)  # 5 second timeout
                    
                    try:
                        status = processor.get_status()
                        logger.debug(f"🔄 Loop #{loop_count}: Bay {bay_id} status retrieved successfully")
                    finally:
                        # Clear the alarm
                        if hasattr(signal, 'SIGALRM'):
                            signal.alarm(0)
                    
                    statuses[bay_id] = status
                    
                    # Update bay tracker
                    logger.debug(f"🔄 Loop #{loop_count}: Updating bay tracker for Bay {bay_id}")
                    bay_tracker.update_bay_status(
                        bay_id=bay_id,
                        vehicle_detected=status['vehicle_detected'],
                        is_connected=status['is_connected'],
                        last_frame_time=status['last_frame_time'],
                        detection_confidence=status['detection_confidence']
                    )
                    logger.debug(f"🔄 Loop #{loop_count}: Bay {bay_id} tracker updated")
                    
                except Exception as e:
                    logger.error(f"🔄 Loop #{loop_count}: ERROR getting status from Bay {bay_id}: {str(e)}")
                    # Create a fallback status
                    statuses[bay_id] = {
                        'bay_id': bay_id,
                        'is_connected': False,
                        'vehicle_detected': False,
                        'last_frame_time': None,
                        'detection_confidence': 0.0
                    }
            
            # Update health monitor using cached statuses
            logger.debug(f"🔄 Loop #{loop_count}: Updating health monitor with {len(statuses)} statuses")
            if health_monitor:
                try:
                    for bay_id, status in statuses.items():
                        health_monitor.update_bay_health(bay_id, status)
                    logger.debug(f"🔄 Loop #{loop_count}: Health monitor updated successfully")
                except Exception as e:
                    logger.error(f"🔄 Loop #{loop_count}: ERROR updating health monitor: {str(e)}")
            
            # Log bay status summary periodically (every 10 seconds)
            config = get_config()
            
            # Debug timing logic
            time_since_last_log = current_time - last_status_log
            if loop_count <= 5 or loop_count % 30 == 0:  # Log first 5 loops and every 30 seconds
                logger.info(f"🔄 Loop #{loop_count}: Time since last status log: {time_since_last_log:.1f}s (need {config.status_log_interval}s)")
            
            logger.debug(f"🔄 Loop #{loop_count}: Checking if time for status summary: {time_since_last_log:.1f}s >= {config.status_log_interval}s")
            
            if current_time - last_status_log >= config.status_log_interval:
                logger.info(f"🔄 Generating bay status summary (loop #{loop_count})...")
                status_summary = []
                
                logger.debug(f"🔄 Loop #{loop_count}: Getting bay statuses from tracker for {config.bay_count} bays")
                
                for bay_id in range(1, config.bay_count + 1):
                    try:
                        logger.debug(f"🔄 Loop #{loop_count}: Getting Bay {bay_id} status from tracker")
                        bay_status = bay_tracker.get_bay_status(bay_id)
                        logger.debug(f"🔄 Loop #{loop_count}: Bay {bay_id} status from tracker: {bay_status}")
                        
                        if bay_status:
                            # Enhanced status display with better emojis and formatting
                            status = bay_status['status']
                            if status == 'inUse':
                                emoji = "🚗"
                                display_status = "InUse"
                            elif status == 'connectionError':
                                emoji = "❌"
                                display_status = "ConnectionLost"
                            elif status == 'outOfService':
                                emoji = "🔧"
                                display_status = "OutOfService"
                            else:  # available
                                emoji = "🅿️"
                                display_status = "Available"
                            
                            # Add connection indicator
                            connection_status = "🟢" if bay_status.get('isConnected', False) else "🔴"
                            status_summary.append(f"Bay {bay_id}: {emoji} {display_status} {connection_status}")
                        else:
                            # Bay status is None - add debug info
                            logger.warning(f"🔄 Loop #{loop_count}: Bay {bay_id} returned None status from tracker")
                            status_summary.append(f"Bay {bay_id}: ❓ NoStatus")
                        
                    except Exception as e:
                        logger.error(f"🔄 Loop #{loop_count}: ERROR getting Bay {bay_id} status: {str(e)}")
                        status_summary.append(f"Bay {bay_id}: ❌ Error")
                
                logger.debug(f"🔄 Loop #{loop_count}: Generated status summary with {len(status_summary)} entries")
                
                if status_summary:
                    logger.info(f"🏪 BAY STATUS SUMMARY: {' | '.join(status_summary)}")
                else:
                    logger.warning("🏪 BAY STATUS SUMMARY: No bay statuses available")
                
                last_status_log = current_time
                logger.debug(f"🔄 Loop #{loop_count}: Status summary completed, next summary in {config.status_log_interval}s")
            
            # Sleep to control update rate
            logger.debug(f"🔄 Loop #{loop_count}: Sleeping for 1 second")
            time.sleep(1)
            
        except Exception as e:
            logger.error(f"💥 CRITICAL ERROR in bay status update thread (loop #{loop_count}): {str(e)}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            logger.error(f"Thread will continue after 5 second delay...")
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
    logger.info("🚀 Starting bay status update thread...")
    update_thread = threading.Thread(target=update_bay_statuses)
    update_thread.daemon = True
    update_thread.start()
    logger.info("✅ Bay status update thread started")
    
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