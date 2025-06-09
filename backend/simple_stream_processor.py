import cv2
import time
import logging
import threading
from datetime import datetime
from simple_detector import SimpleCarDetector

# Configure logging
logger = logging.getLogger('simple_stream_processor')

class SimpleRTSPStreamProcessor:
    """
    Simplified RTSP stream processor using background subtraction instead of YOLOv4.
    Much more accurate for overhead car wash bay cameras!
    """
    
    def __init__(self, bay_id, rtsp_url, reconnect_interval=5, max_reconnect_attempts=10):
        """
        Initialize the simple RTSP stream processor.
        
        Args:
            bay_id: ID of the bay associated with this stream
            rtsp_url: URL of the RTSP stream
            reconnect_interval: Time to wait between reconnection attempts (seconds)
            max_reconnect_attempts: Maximum number of reconnection attempts
        """
        self.bay_id = bay_id
        self.rtsp_url = rtsp_url
        self.reconnect_interval = reconnect_interval
        self.max_reconnect_attempts = max_reconnect_attempts
        
        # Create simple detector for this bay
        self.detector = SimpleCarDetector()
        
        # Stream state
        self.cap = None
        self.is_connected = False
        self.is_running = False
        self.reconnect_attempts = 0
        self.last_frame_time = None
        self.last_successful_connection = None
        self.last_frame = None
        
        # Detection results
        self.car_detected = False
        self.last_detection_time = None
        self.detection_confidence = 0.0
        
        # Processing thread
        self.thread = None
        self.lock = threading.Lock()
    
    def connect(self):
        """Connect to the RTSP stream."""
        logger.info(f"Connecting to RTSP stream for Bay {self.bay_id}: {self.rtsp_url}")
        
        try:
            # OpenCV connection to RTSP stream
            self.cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
            
            # Check if connection is successful
            if not self.cap.isOpened():
                logger.error(f"Failed to open RTSP stream for Bay {self.bay_id}")
                self.is_connected = False
                return False
            
            # Set buffer size and timeout
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            
            # Update connection state
            self.is_connected = True
            self.last_successful_connection = datetime.now()
            self.reconnect_attempts = 0
            
            logger.info(f"Successfully connected to RTSP stream for Bay {self.bay_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to RTSP stream for Bay {self.bay_id}: {str(e)}")
            self.is_connected = False
            return False
    
    def disconnect(self):
        """Disconnect from the RTSP stream."""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        
        self.is_connected = False
        logger.info(f"Disconnected from RTSP stream for Bay {self.bay_id}")
    
    def reconnect(self):
        """Attempt to reconnect to the RTSP stream."""
        self.reconnect_attempts += 1
        
        if self.reconnect_attempts > self.max_reconnect_attempts:
            logger.error(f"Exceeded maximum reconnection attempts for Bay {self.bay_id}")
            return False
        
        logger.info(f"Reconnection attempt {self.reconnect_attempts}/{self.max_reconnect_attempts} for Bay {self.bay_id}")
        
        # Disconnect if currently connected
        if self.is_connected:
            self.disconnect()
        
        # Wait before reconnecting
        time.sleep(self.reconnect_interval)
        
        # Attempt to connect
        return self.connect()
    
    def get_frame(self):
        """Get a frame from the RTSP stream."""
        if not self.is_connected or self.cap is None:
            return None
        
        try:
            # Read frame from stream
            ret, frame = self.cap.read()
            
            if not ret or frame is None:
                logger.warning(f"Failed to read frame from RTSP stream for Bay {self.bay_id}")
                return None
            
            # Update last frame time
            self.last_frame_time = datetime.now()
            self.last_frame = frame
            
            return frame
            
        except Exception as e:
            logger.error(f"Error getting frame from RTSP stream for Bay {self.bay_id}: {str(e)}")
            return None
    
    def process_stream(self):
        """Process the RTSP stream continuously."""
        logger.info(f"Starting simple stream processing for Bay {self.bay_id}")
        
        while self.is_running:
            # Check if connected
            if not self.is_connected:
                if not self.reconnect():
                    # If reconnection failed, wait before trying again
                    time.sleep(self.reconnect_interval)
                    continue
            
            # Get frame
            frame = self.get_frame()
            
            if frame is None:
                logger.warning(f"Empty frame received for Bay {self.bay_id}, attempting reconnect")
                self.reconnect()
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
        """Get the current status of the stream processor."""
        with self.lock:
            return {
                'bay_id': self.bay_id,
                'is_connected': self.is_connected,
                'vehicle_detected': self.car_detected,
                'last_frame_time': self.last_frame_time,
                'last_detection_time': self.last_detection_time,
                'detection_confidence': self.detection_confidence,
                'reconnect_attempts': self.reconnect_attempts,
                'last_successful_connection': self.last_successful_connection
            }
    
    def reset_background(self):
        """Reset the background model for this bay (call when known empty)"""
        logger.info(f"Resetting background model for Bay {self.bay_id}")
        self.detector.reset_background()