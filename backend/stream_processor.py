import cv2
import time
import logging
import threading
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('stream_processor')

class RTSPStreamProcessor:
    """
    Class for processing RTSP video streams and detecting vehicles.
    """
    def __init__(self, bay_id, rtsp_url, detector, 
                 reconnect_interval=5, max_reconnect_attempts=10):
        """
        Initialize the RTSP stream processor.
        
        Args:
            bay_id: ID of the bay associated with this stream
            rtsp_url: URL of the RTSP stream
            detector: Instance of VehicleDetector
            reconnect_interval: Time to wait between reconnection attempts (seconds)
            max_reconnect_attempts: Maximum number of reconnection attempts
        """
        self.bay_id = bay_id
        self.rtsp_url = rtsp_url
        self.detector = detector
        self.reconnect_interval = reconnect_interval
        self.max_reconnect_attempts = max_reconnect_attempts
        
        # Stream state
        self.cap = None
        self.is_connected = False
        self.is_running = False
        self.reconnect_attempts = 0
        self.last_frame_time = None
        self.last_successful_connection = None
        self.last_frame = None
        
        # Detection results
        self.vehicle_detected = False
        self.last_detection_time = None
        self.detection_confidence = 0.0
        
        # Processing thread
        self.thread = None
        self.lock = threading.Lock()
    
    def connect(self):
        """
        Connect to the RTSP stream.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
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
        """
        Disconnect from the RTSP stream.
        """
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        
        self.is_connected = False
        logger.info(f"Disconnected from RTSP stream for Bay {self.bay_id}")
    
    def reconnect(self):
        """
        Attempt to reconnect to the RTSP stream.
        
        Returns:
            bool: True if reconnection successful, False otherwise
        """
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
        """
        Get a frame from the RTSP stream.
        
        Returns:
            frame: The captured frame or None if failed
        """
        if not self.is_connected or self.cap is None:
            logger.warning(f"Cannot get frame: Not connected to RTSP stream for Bay {self.bay_id}")
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
        """
        Process the RTSP stream continuously.
        """
        logger.info(f"Starting stream processing for Bay {self.bay_id}")
        
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
            
            # Detect vehicles
            try:
                with self.lock:
                    detected, detections = self.detector.detect_vehicles(frame)
                    
                    # Update detection state
                    self.vehicle_detected = detected
                    self.last_detection_time = datetime.now()
                    
                    # Update confidence if vehicles detected
                    if detected and detections:
                        # Use highest confidence detection
                        self.detection_confidence = max(d['confidence'] for d in detections)
                        # Log detection details for debugging
                        detection_info = []
                        for d in detections:
                            detection_info.append(f"{d['class_name']}({d['confidence']:.2f})")
                        logger.info(f"Bay {self.bay_id}: Vehicle detected - {', '.join(detection_info)}")
                    else:
                        self.detection_confidence = 0.0
                    
                    logger.debug(f"Bay {self.bay_id}: Vehicle detected: {detected}, " 
                                f"Confidence: {self.detection_confidence:.2f}")
                    
            except Exception as e:
                logger.error(f"Error detecting vehicles for Bay {self.bay_id}: {str(e)}")
            
            # Sleep to control processing rate (adjust as needed)
            time.sleep(0.1)
    
    def start(self):
        """
        Start processing the RTSP stream in a separate thread.
        """
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
        
        logger.info(f"Stream processor started for Bay {self.bay_id}")
    
    def stop(self):
        """
        Stop processing the RTSP stream.
        """
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
        
        logger.info(f"Stream processor stopped for Bay {self.bay_id}")
    
    def get_status(self):
        """
        Get the current status of the stream processor.
        
        Returns:
            dict: Status information
        """
        with self.lock:
            return {
                'bay_id': self.bay_id,
                'is_connected': self.is_connected,
                'vehicle_detected': self.vehicle_detected,
                'last_frame_time': self.last_frame_time,
                'last_detection_time': self.last_detection_time,
                'detection_confidence': self.detection_confidence,
                'reconnect_attempts': self.reconnect_attempts,
                'last_successful_connection': self.last_successful_connection
            }
