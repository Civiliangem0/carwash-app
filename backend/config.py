"""
Centralized configuration for the car wash detection system.
"""
import os
from dataclasses import dataclass
from typing import Dict

@dataclass
class DetectionConfig:
    """Configuration for car detection parameters."""
    # Background subtraction settings
    learning_rate: float = 0.001
    min_contour_area: int = 2000
    bay_center_ratio: float = 0.4
    confidence_threshold: float = 0.1
    
    # Learning phase
    learning_frames: int = 100
    
    # Logging
    confidence_change_threshold: float = 0.2  # Only log when confidence changes by this much
    empty_bay_log_interval: int = 100  # Log empty bay every N frames

@dataclass
class StatusConfig:
    """Configuration for bay status transitions."""
    # Asymmetric thresholds for hysteresis (prevents flickering)
    available_to_inuse_threshold: int = 2      # Fast transition: 2 detections (~2 seconds)
    inuse_to_available_threshold: int = 8      # Slow transition: 8 detections (~8 seconds)
    
    # Connection and timeout settings
    connection_grace_period: int = 10          # Seconds to wait before marking disconnected bay as available
    frame_timeout: int = 30                    # Seconds before marking bay as connection error
    customer_connection_timeout: int = 60      # Seconds before showing ConnectionLost to customers

@dataclass
class RTSPConfig:
    """Configuration for RTSP stream handling."""
    # Connection settings
    max_reconnect_attempts: int = 10
    base_reconnect_interval: int = 2           # Base seconds between reconnection attempts (faster for car wash)
    max_reconnect_interval: int = 60           # Max seconds for exponential backoff
    
    # Stream settings
    buffer_size: int = 1
    target_fps: int = 10
    connection_timeout: int = 15               # Seconds to wait for initial connection
    
    # Quality degradation settings
    quality_levels: Dict[str, Dict] = None
    
    def __post_init__(self):
        if self.quality_levels is None:
            self.quality_levels = {
                'high': {'fps': 10, 'buffer_size': 1},
                'medium': {'fps': 5, 'buffer_size': 2},
                'low': {'fps': 2, 'buffer_size': 3}
            }

@dataclass
class SystemConfig:
    """Main system configuration."""
    # Bay configuration
    bay_count: int = 4
    rtsp_urls: Dict[int, str] = None
    
    # Monitoring
    status_update_interval: int = 1            # Seconds between status updates
    status_log_interval: int = 10              # Seconds between status summary logs (more frequent for car wash)
    health_check_interval: int = 60            # Seconds between health checks
    
    # API settings
    api_host: str = '0.0.0.0'
    api_port: int = 5000
    secret_key: str = 'dev-secret-key'
    
    # Component configs
    detection: DetectionConfig = None
    status: StatusConfig = None
    rtsp: RTSPConfig = None
    
    def __post_init__(self):
        # Initialize sub-configs
        if self.detection is None:
            self.detection = DetectionConfig()
        if self.status is None:
            self.status = StatusConfig()
        if self.rtsp is None:
            self.rtsp = RTSPConfig()
        
        # Load RTSP URLs from environment if not provided
        if self.rtsp_urls is None:
            self.rtsp_urls = {
                1: os.environ.get('RTSP_URL_1', 'rtsp://192.168.1.74:7447/VJ1fB8D4d03nIwKF'),
                2: os.environ.get('RTSP_URL_2', 'rtsp://192.168.1.74:7447/zfDlcWJLTq10A49M'),
                3: os.environ.get('RTSP_URL_3', 'rtsp://192.168.1.74:7447/18JUhav6VfoOMVS0'),
                4: os.environ.get('RTSP_URL_4', 'rtsp://192.168.1.74:7447/BSPtMFwAXLncNdx0')
            }
        
        # Apply environment variable overrides
        self._apply_env_overrides()
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides to configuration."""
        # Detection overrides
        if os.getenv('DETECTION_LEARNING_RATE'):
            self.detection.learning_rate = float(os.getenv('DETECTION_LEARNING_RATE'))
        if os.getenv('DETECTION_MIN_AREA'):
            self.detection.min_contour_area = int(os.getenv('DETECTION_MIN_AREA'))
        if os.getenv('DETECTION_CENTER_RATIO'):
            self.detection.bay_center_ratio = float(os.getenv('DETECTION_CENTER_RATIO'))
        
        # Status overrides
        if os.getenv('STATUS_FAST_THRESHOLD'):
            self.status.available_to_inuse_threshold = int(os.getenv('STATUS_FAST_THRESHOLD'))
        if os.getenv('STATUS_SLOW_THRESHOLD'):
            self.status.inuse_to_available_threshold = int(os.getenv('STATUS_SLOW_THRESHOLD'))
        
        # RTSP overrides
        if os.getenv('RTSP_TARGET_FPS'):
            self.rtsp.target_fps = int(os.getenv('RTSP_TARGET_FPS'))
        if os.getenv('RTSP_RECONNECT_INTERVAL'):
            self.rtsp.base_reconnect_interval = int(os.getenv('RTSP_RECONNECT_INTERVAL'))
        
        # System overrides
        if os.getenv('PORT'):
            self.api_port = int(os.getenv('PORT'))
        if os.getenv('SECRET_KEY'):
            self.secret_key = os.getenv('SECRET_KEY')

# Global configuration instance
config = SystemConfig()

def reload_config():
    """Reload configuration from environment variables."""
    global config
    config = SystemConfig()
    return config

def get_config() -> SystemConfig:
    """Get the current system configuration."""
    return config