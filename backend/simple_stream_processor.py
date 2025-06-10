import cv2
import time
import logging
import threading
import math
from datetime import datetime
from simple_detector import SimpleCarDetector
from config import get_config

# Configure logging
logger = logging.getLogger('simple_stream_processor')

class SimpleRTSPStreamProcessor:
    """
    Advanced RTSP stream processor with exponential backoff and connection recovery.
    """
    
    def __init__(self, bay_id, rtsp_url):
        """
        Initialize the advanced RTSP stream processor.
        """
        self.bay_id = bay_id
        self.rtsp_url = rtsp_url
        
        # Load configuration
        config = get_config()
        self.max_reconnect_attempts = config.rtsp.max_reconnect_attempts
        self.base_reconnect_interval = config.rtsp.base_reconnect_interval
        self.max_reconnect_interval = config.rtsp.max_reconnect_interval
        self.connection_timeout = config.rtsp.connection_timeout
        self.target_fps = config.rtsp.target_fps
        self.buffer_size = config.rtsp.buffer_size
        
        # Create simple detector for this bay with bay_id for background loading
        self.detector = SimpleCarDetector(bay_id=bay_id)
        
        # Stream state
        self.cap = None
        self.is_connected = False
        self.is_running = False
        self.reconnect_attempts = 0
        self.last_frame_time = None
        self.last_successful_connection = None
        self.last_frame = None
        self.connection_start_time = None
        
        # Advanced connection management
        self.consecutive_failures = 0
        self.total_reconnects = 0
        self.last_error = None
        self.quality_level = 'high'  # high, medium, low
        
        # Detection results
        self.car_detected = False
        self.last_detection_time = None
        self.detection_confidence = 0.0
        
        # Performance tracking
        self.frames_processed = 0
        self.frames_failed = 0
        self.average_fps = 0.0
        
        # Processing thread
        self.thread = None
        self.lock = threading.Lock()
    
    def _get_current_quality_settings(self):
        """Get current quality settings based on connection performance."""
        config = get_config()
        return config.rtsp.quality_levels.get(self.quality_level, {
            'fps': self.target_fps,
            'buffer_size': self.buffer_size
        })
    
    def _degrade_quality(self):
        """Degrade stream quality to improve stability."""
        if self.quality_level == 'high':
            self.quality_level = 'medium'
            logger.warning(f"Bay {self.bay_id}: Degrading to MEDIUM quality due to connection issues")
        elif self.quality_level == 'medium':
            self.quality_level = 'low'
            logger.warning(f"Bay {self.bay_id}: Degrading to LOW quality due to connection issues")
        else:
            logger.warning(f"Bay {self.bay_id}: Already at lowest quality")
    
    def connect(self):
        """Advanced RTSP connection with quality adaptation."""
        self.connection_start_time = datetime.now()
        quality_settings = self._get_current_quality_settings()
        
        logger.info(f"Bay {self.bay_id}: Connecting to RTSP stream (quality: {self.quality_level})")
        logger.debug(f"Bay {self.bay_id}: URL: {self.rtsp_url}")
        
        try:
            # Release any existing connection
            if self.cap is not None:
                self.cap.release()
                self.cap = None
            
            # Create new connection with timeout
            self.cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
            
            # Configure stream settings
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, quality_settings['buffer_size'])
            self.cap.set(cv2.CAP_PROP_FPS, quality_settings['fps'])
            
            # Additional settings to reduce H.264 errors
            self.cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'H264'))
            
            # Check connection by trying to read a frame
            if not self.cap.isOpened():
                raise Exception("Failed to open RTSP stream")
            
            # Test frame read with timeout
            start_time = time.time()
            ret, test_frame = self.cap.read()
            read_time = time.time() - start_time
            
            if not ret or test_frame is None:
                raise Exception("Failed to read test frame")
            
            if read_time > 5.0:  # If frame read takes too long
                logger.warning(f"Bay {self.bay_id}: Slow frame read ({read_time:.1f}s) - connection may be unstable")
            
            # Connection successful!
            self.is_connected = True
            self.last_successful_connection = datetime.now()
            self.consecutive_failures = 0
            self.last_error = None
            
            connection_time = (datetime.now() - self.connection_start_time).total_seconds()
            logger.info(f"✅ Bay {self.bay_id}: Connected successfully in {connection_time:.1f}s (quality: {self.quality_level})")
            
            return True
            
        except Exception as e:
            self.is_connected = False
            self.consecutive_failures += 1
            self.last_error = str(e)
            
            logger.error(f"❌ Bay {self.bay_id}: Connection failed: {str(e)}")
            
            # Auto-degrade quality after repeated failures
            if self.consecutive_failures >= 3:
                self._degrade_quality()
                self.consecutive_failures = 0  # Reset counter after degradation
            
            return False
    
    def disconnect(self):
        """Disconnect from the RTSP stream."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        
        self.is_connected = False
        logger.info(f"Disconnected from RTSP stream for Bay {self.bay_id}")
    
    def _calculate_backoff_delay(self):
        """Calculate exponential backoff delay."""
        # Exponential backoff: base_interval * (2 ^ attempt) with jitter
        delay = self.base_reconnect_interval * (2 ** min(self.reconnect_attempts, 6))
        delay = min(delay, self.max_reconnect_interval)  # Cap at max interval
        
        # Add jitter (±25%) to prevent thundering herd
        jitter = delay * 0.25 * (time.time() % 1 - 0.5)  # -12.5% to +12.5%
        delay += jitter
        
        return max(1.0, delay)  # Minimum 1 second
    
    def reconnect(self):
        """Advanced reconnection with exponential backoff."""
        self.reconnect_attempts += 1
        self.total_reconnects += 1
        
        if self.reconnect_attempts > self.max_reconnect_attempts:
            logger.error(f"🚫 Bay {self.bay_id}: Exceeded maximum reconnection attempts ({self.max_reconnect_attempts})")
            logger.error(f"Bay {self.bay_id}: Total reconnects this session: {self.total_reconnects}")
            return False
        
        # Calculate backoff delay
        delay = self._calculate_backoff_delay()
        
        logger.info(f"🔄 Bay {self.bay_id}: Reconnection attempt {self.reconnect_attempts}/{self.max_reconnect_attempts}")
        logger.info(f"Bay {self.bay_id}: Waiting {delay:.1f}s before retry (exponential backoff)")
        
        # Disconnect if currently connected
        if self.is_connected:
            self.disconnect()
        
        # Wait with backoff
        time.sleep(delay)
        
        # Attempt to connect
        success = self.connect()
        
        if success:
            logger.info(f"🎉 Bay {self.bay_id}: Reconnection successful after {self.reconnect_attempts} attempts")
            self.reconnect_attempts = 0  # Reset on success
        
        return success
    
    def get_frame(self):
        """Advanced frame reading with error tracking."""
        if not self.is_connected or self.cap is None:
            return None
        
        try:
            # Read frame from stream with timeout awareness
            start_time = time.time()
            ret, frame = self.cap.read()
            read_time = time.time() - start_time
            
            if not ret or frame is None:
                self.frames_failed += 1
                
                # Don't spam logs for every failed frame
                if self.frames_failed % 10 == 1:  # Log every 10th failure
                    logger.warning(f"Bay {self.bay_id}: Frame read failed (#{self.frames_failed})")
                
                return None
            
            # Successful frame read
            self.frames_processed += 1
            self.last_frame_time = datetime.now()
            self.last_frame = frame
            
            # Track performance
            if self.frames_processed % 100 == 0:  # Update FPS every 100 frames
                self._update_performance_metrics()
            
            # Warn about slow frame reads (potential network issues)
            if read_time > 1.0:
                logger.warning(f"Bay {self.bay_id}: Slow frame read ({read_time:.1f}s) - network congestion?")
            
            return frame
            
        except Exception as e:
            self.frames_failed += 1
            
            # Log error occasionally
            if self.frames_failed % 10 == 1:
                logger.error(f"Bay {self.bay_id}: Frame read exception (#{self.frames_failed}): {str(e)}")
            
            return None
    
    def _update_performance_metrics(self):
        """Update performance tracking metrics."""
        if self.last_successful_connection:
            elapsed = (datetime.now() - self.last_successful_connection).total_seconds()
            if elapsed > 0:
                self.average_fps = self.frames_processed / elapsed
                
                # Log performance occasionally
                success_rate = (self.frames_processed / (self.frames_processed + self.frames_failed)) * 100
                logger.debug(f"Bay {self.bay_id}: Performance - FPS: {self.average_fps:.1f}, Success: {success_rate:.1f}%")
    
    def process_stream(self):
        """Process the RTSP stream continuously."""
        logger.info(f"Starting simple stream processing for Bay {self.bay_id}")
        
        while self.is_running:
            # Check if connected
            if not self.is_connected:
                if not self.reconnect():
                    # If reconnection failed, wait before trying again
                    time.sleep(self.base_reconnect_interval)
                    continue
            
            # Get frame
            frame = self.get_frame()
            
            if frame is None:
                logger.warning(f"Empty frame received for Bay {self.bay_id}, attempting reconnect")
                if not self.reconnect():
                    # If reconnection failed, wait before trying again with the base interval
                    time.sleep(self.base_reconnect_interval)
                continue
            
            # Detect cars using simple background subtraction
            try:
                with self.lock:
                    detected, confidence = self.detector.detect_car(frame, self.bay_id)
                    
                    # Update detection state
                    self.car_detected = detected
                    self.detection_confidence = confidence
                    if detected:
                        self.last_detection_time = datetime.now()
                        logger.debug(f"Bay {self.bay_id}: Car detected (conf: {confidence:.2f})")
                    
            except Exception as e:
                logger.error(f"Error detecting cars for Bay {self.bay_id}: {str(e)}")
            
            # Sleep to control processing rate (process ~10 FPS)
            time.sleep(0.1)
    
    def start(self):
        """Start processing the RTSP stream in a separate thread."""
        if self.is_running:
            logger.warning(f"Stream processor for Bay {self.bay_id} is already running")
            return
        
        # Connect to stream
        if not self.connect():
            logger.error(f"Failed to start stream processor for Bay {self.bay_id}: Could not connect")
            return
        
        # Set running state
        self.is_running = True
        
        # Start processing thread
        self.thread = threading.Thread(target=self.process_stream)
        self.thread.daemon = True
        self.thread.start()
        
        logger.info(f"Simple stream processor started for Bay {self.bay_id}")
    
    def stop(self):
        """Stop processing the RTSP stream."""
        if not self.is_running:
            logger.warning(f"Stream processor for Bay {self.bay_id} is not running")
            return
        
        # Set running state
        self.is_running = False
        
        # Wait for thread to finish
        if self.thread is not None:
            self.thread.join(timeout=1.0)
            self.thread = None
        
        # Disconnect from stream
        self.disconnect()
        
        logger.info(f"Simple stream processor stopped for Bay {self.bay_id}")
    
    def get_status(self):
        """Get comprehensive status of the stream processor."""
        with self.lock:
            return {
                'bay_id': self.bay_id,
                'is_connected': self.is_connected,
                'vehicle_detected': self.car_detected,
                'last_frame_time': self.last_frame_time,
                'last_detection_time': self.last_detection_time,
                'detection_confidence': self.detection_confidence,
                'reconnect_attempts': self.reconnect_attempts,
                'last_successful_connection': self.last_successful_connection,
                
                # New metrics for health monitoring
                'total_reconnects': self.total_reconnects,
                'consecutive_failures': self.consecutive_failures,
                'quality_level': self.quality_level,
                'last_error': self.last_error,
                'frames_processed': self.frames_processed,
                'frames_failed': self.frames_failed,
                'average_fps': self.average_fps
            }
    
    def reset_background(self):
        """Reset the background model for this bay (call when known empty)"""
        logger.info(f"Resetting background model for Bay {self.bay_id}")
        self.detector.reset_background()