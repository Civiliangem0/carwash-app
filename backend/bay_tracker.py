import logging
import threading
from datetime import datetime, timedelta
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('bay_tracker')

class BayStatus(Enum):
    """
    Enum for bay status.
    """
    AVAILABLE = "available"
    IN_USE = "inUse"
    OUT_OF_SERVICE = "outOfService"
    CONNECTION_ERROR = "connectionError"

class BayTracker:
    """
    Class for tracking the status of car wash bays.
    """
    def __init__(self, bay_count=4, status_change_threshold=5, error_timeout=30):
        """
        Initialize the bay tracker.
        
        Args:
            bay_count: Number of bays to track
            status_change_threshold: Number of consecutive detections needed to change status
            error_timeout: Time in seconds after which to mark a bay as having connection error
        """
        self.bay_count = bay_count
        self.status_change_threshold = status_change_threshold
        self.error_timeout = error_timeout
        
        # Initialize bay statuses
        self.bays = {}
        for bay_id in range(1, bay_count + 1):
            self.bays[bay_id] = {
                'status': BayStatus.AVAILABLE,
                'last_updated': datetime.now(),
                'consecutive_detections': 0,
                'consecutive_non_detections': 0,
                'last_frame_time': None,
                'detection_confidence': 0.0,
                'is_connected': False
            }
        
        # Thread safety
        self.lock = threading.Lock()
        
        logger.info(f"Bay tracker initialized with {bay_count} bays")
    
    def update_bay_status(self, bay_id, vehicle_detected, is_connected, 
                         last_frame_time=None, detection_confidence=0.0):
        """
        Update the status of a bay based on vehicle detection.
        
        Args:
            bay_id: ID of the bay to update
            vehicle_detected: Boolean indicating if a vehicle was detected
            is_connected: Boolean indicating if the stream is connected
            last_frame_time: Timestamp of the last frame processed
            detection_confidence: Confidence of the detection
        """
        if bay_id not in self.bays:
            logger.error(f"Invalid bay ID: {bay_id}")
            return
        
        with self.lock:
            bay = self.bays[bay_id]
            
            # Update connection status
            bay['is_connected'] = is_connected
            
            # Update frame time if provided
            if last_frame_time is not None:
                bay['last_frame_time'] = last_frame_time
            
            # Update detection confidence
            bay['detection_confidence'] = detection_confidence
            
            # Check for connection error
            if not is_connected:
                if bay['status'] != BayStatus.CONNECTION_ERROR:
                    bay['status'] = BayStatus.CONNECTION_ERROR
                    bay['last_updated'] = datetime.now()
                    logger.warning(f"Bay {bay_id} marked as CONNECTION_ERROR due to stream disconnection")
                return
            
            # Check for frame timeout
            if bay['last_frame_time'] is not None:
                time_since_last_frame = datetime.now() - bay['last_frame_time']
                if time_since_last_frame.total_seconds() > self.error_timeout:
                    if bay['status'] != BayStatus.CONNECTION_ERROR:
                        bay['status'] = BayStatus.CONNECTION_ERROR
                        bay['last_updated'] = datetime.now()
                        logger.warning(f"Bay {bay_id} marked as CONNECTION_ERROR due to frame timeout")
                    return
            
            # Update detection counters
            if vehicle_detected:
                bay['consecutive_detections'] += 1
                bay['consecutive_non_detections'] = 0
            else:
                bay['consecutive_detections'] = 0
                bay['consecutive_non_detections'] += 1
            
            # Update bay status based on detection counters
            current_status = bay['status']
            new_status = current_status
            
            # Change to IN_USE if enough consecutive detections
            if (current_status == BayStatus.AVAILABLE or 
                current_status == BayStatus.CONNECTION_ERROR) and \
               bay['consecutive_detections'] >= self.status_change_threshold:
                new_status = BayStatus.IN_USE
            
            # Change to AVAILABLE if enough consecutive non-detections
            elif current_status == BayStatus.IN_USE and \
                 bay['consecutive_non_detections'] >= self.status_change_threshold:
                new_status = BayStatus.AVAILABLE
            
            # Update status if changed
            if new_status != current_status:
                bay['status'] = new_status
                bay['last_updated'] = datetime.now()
                logger.info(f"Bay {bay_id} status changed from {current_status.value} to {new_status.value}")
    
    def get_bay_status(self, bay_id):
        """
        Get the current status of a bay.
        
        Args:
            bay_id: ID of the bay to get status for
            
        Returns:
            dict: Bay status information
        """
        if bay_id not in self.bays:
            logger.error(f"Invalid bay ID: {bay_id}")
            return None
        
        with self.lock:
            bay = self.bays[bay_id]
            return {
                'id': bay_id,
                'status': bay['status'].value,
                'lastUpdated': bay['last_updated'].isoformat(),
                'isConnected': bay['is_connected'],
                'detectionConfidence': bay['detection_confidence']
            }
    
    def get_all_bay_statuses(self):
        """
        Get the current status of all bays.
        
        Returns:
            list: List of bay status dictionaries
        """
        with self.lock:
            return [self.get_bay_status(bay_id) for bay_id in range(1, self.bay_count + 1)]
    
    def set_bay_out_of_service(self, bay_id, out_of_service=True):
        """
        Manually set a bay as out of service or back in service.
        
        Args:
            bay_id: ID of the bay to update
            out_of_service: Boolean indicating if bay should be out of service
        """
        if bay_id not in self.bays:
            logger.error(f"Invalid bay ID: {bay_id}")
            return
        
        with self.lock:
            bay = self.bays[bay_id]
            
            if out_of_service:
                bay['status'] = BayStatus.OUT_OF_SERVICE
            else:
                # Reset to available when bringing back to service
                bay['status'] = BayStatus.AVAILABLE
                bay['consecutive_detections'] = 0
                bay['consecutive_non_detections'] = 0
            
            bay['last_updated'] = datetime.now()
            logger.info(f"Bay {bay_id} manually set to {'OUT_OF_SERVICE' if out_of_service else 'AVAILABLE'}")
