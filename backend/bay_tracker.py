import logging
import threading
from datetime import datetime, timedelta
from enum import Enum
from config import get_config

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
    Advanced bay tracker with asymmetric transitions and connection error recovery.
    """
    def __init__(self, bay_count=None):
        """
        Initialize the bay tracker with configuration-based settings.
        """
        config = get_config()
        
        self.bay_count = bay_count or config.bay_count
        
        # Asymmetric thresholds for hysteresis (prevents status flickering)
        self.available_to_inuse_threshold = config.status.available_to_inuse_threshold  # Fast: 2 detections
        self.inuse_to_available_threshold = config.status.inuse_to_available_threshold  # Slow: 8 detections
        
        # Connection management
        self.frame_timeout = config.status.frame_timeout
        self.connection_grace_period = config.status.connection_grace_period
        
        # Initialize bay statuses
        self.bays = {}
        for bay_id in range(1, self.bay_count + 1):
            self.bays[bay_id] = {
                'status': BayStatus.AVAILABLE,
                'last_updated': datetime.now(),
                'consecutive_detections': 0,
                'consecutive_non_detections': 0,
                'last_frame_time': None,
                'detection_confidence': 0.0,
                'is_connected': False,
                'last_connection_time': None,      # Track when connection was established
                'last_disconnection_time': None,   # Track when connection was lost
                'connection_recovery_pending': False  # Flag for recovery state
            }
        
        # Thread safety
        self.lock = threading.Lock()
        
        logger.info(f"Bay tracker initialized with {self.bay_count} bays")
        logger.info(f"Asymmetric thresholds: available→inUse={self.available_to_inuse_threshold}, inUse→available={self.inuse_to_available_threshold}")
    
    def update_bay_status(self, bay_id, vehicle_detected, is_connected, 
                         last_frame_time=None, detection_confidence=0.0):
        """
        Advanced bay status update with connection recovery and asymmetric transitions.
        """
        if bay_id not in self.bays:
            logger.error(f"Invalid bay ID: {bay_id}")
            return
        
        with self.lock:
            bay = self.bays[bay_id]
            current_time = datetime.now()
            
            # Track connection state changes
            was_connected = bay['is_connected']
            bay['is_connected'] = is_connected
            
            # Update frame time if provided
            if last_frame_time is not None:
                bay['last_frame_time'] = last_frame_time
            
            # Update detection confidence
            bay['detection_confidence'] = detection_confidence
            
            # Handle connection state changes
            if is_connected and not was_connected:
                # Connection recovered!
                bay['last_connection_time'] = current_time
                bay['connection_recovery_pending'] = True
                logger.info(f"🔌 Bay {bay_id} connection RECOVERED")
                
            elif not is_connected and was_connected:
                # Connection lost
                bay['last_disconnection_time'] = current_time
                bay['connection_recovery_pending'] = False
                logger.warning(f"⚠️ Bay {bay_id} connection LOST")
            
            # Handle disconnected streams
            if not is_connected:
                if bay['status'] != BayStatus.CONNECTION_ERROR:
                    bay['status'] = BayStatus.CONNECTION_ERROR
                    bay['last_updated'] = current_time
                    logger.warning(f"Bay {bay_id} marked as CONNECTION_ERROR due to stream disconnection")
                return
            
            # Handle frame timeout (even when "connected")
            if bay['last_frame_time'] is not None:
                time_since_last_frame = current_time - bay['last_frame_time']
                if time_since_last_frame.total_seconds() > self.frame_timeout:
                    if bay['status'] != BayStatus.CONNECTION_ERROR:
                        bay['status'] = BayStatus.CONNECTION_ERROR
                        bay['last_updated'] = current_time
                        logger.warning(f"Bay {bay_id} marked as CONNECTION_ERROR due to frame timeout")
                    return
            
            # ✅ CONNECTION IS GOOD - Handle status recovery and detection logic
            current_status = bay['status']
            new_status = current_status
            
            # CRITICAL FIX: Auto-recover from CONNECTION_ERROR when stream is working
            if current_status == BayStatus.CONNECTION_ERROR and is_connected:
                # Apply grace period to avoid immediate flip-flopping
                if (bay['last_connection_time'] and 
                    (current_time - bay['last_connection_time']).total_seconds() >= self.connection_grace_period):
                    
                    new_status = BayStatus.AVAILABLE
                    bay['consecutive_detections'] = 0
                    bay['consecutive_non_detections'] = 0
                    bay['connection_recovery_pending'] = False
                    logger.info(f"🚀 Bay {bay_id} AUTO-RECOVERED from connectionError → available")
            
            # Skip detection logic during recovery grace period
            if bay['connection_recovery_pending'] and bay['last_connection_time']:
                grace_elapsed = (current_time - bay['last_connection_time']).total_seconds()
                if grace_elapsed < self.connection_grace_period:
                    logger.debug(f"Bay {bay_id}: In recovery grace period ({grace_elapsed:.1f}s/{self.connection_grace_period}s)")
                    return
                else:
                    bay['connection_recovery_pending'] = False
            
            # Update detection counters
            if vehicle_detected:
                bay['consecutive_detections'] += 1
                bay['consecutive_non_detections'] = 0
            else:
                bay['consecutive_detections'] = 0
                bay['consecutive_non_detections'] += 1
            
            # ASYMMETRIC TRANSITIONS (Hysteresis to prevent flickering)
            
            # FAST transition: available → inUse (2 detections, ~2 seconds)
            if (current_status == BayStatus.AVAILABLE and 
                bay['consecutive_detections'] >= self.available_to_inuse_threshold):
                new_status = BayStatus.IN_USE
                logger.debug(f"Bay {bay_id}: FAST transition available→inUse ({bay['consecutive_detections']}/{self.available_to_inuse_threshold})")
            
            # SLOW transition: inUse → available (8 detections, ~8 seconds)  
            elif (current_status == BayStatus.IN_USE and 
                  bay['consecutive_non_detections'] >= self.inuse_to_available_threshold):
                new_status = BayStatus.AVAILABLE
                logger.debug(f"Bay {bay_id}: SLOW transition inUse→available ({bay['consecutive_non_detections']}/{self.inuse_to_available_threshold})")
            
            # Log current detection state
            if vehicle_detected:
                logger.debug(f"Bay {bay_id}: Vehicle detected, consecutive: {bay['consecutive_detections']}/{self.available_to_inuse_threshold}")
            else:
                logger.debug(f"Bay {bay_id}: Empty, consecutive: {bay['consecutive_non_detections']}/{self.inuse_to_available_threshold}")
            
            # Apply status change
            if new_status != current_status:
                bay['status'] = new_status
                bay['last_updated'] = current_time
                logger.info(f"🔄 Bay {bay_id} status changed: {current_status.value} → {new_status.value}")
            else:
                logger.debug(f"Bay {bay_id}: Status remains {current_status.value}")
    
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
