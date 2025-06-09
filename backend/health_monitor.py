"""
Advanced health monitoring and diagnostics for the car wash detection system.
"""
import logging
import threading
import time
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import Dict, List, Optional
from config import get_config

logger = logging.getLogger('health_monitor')

@dataclass
class ConnectionHealth:
    """Health metrics for a single bay's connection."""
    bay_id: int
    is_connected: bool
    last_successful_connection: Optional[datetime]
    total_reconnects: int
    consecutive_failures: int
    average_fps: float
    frames_processed: int
    frames_failed: int
    quality_level: str
    last_error: Optional[str]
    uptime_percentage: float

@dataclass
class SystemHealth:
    """Overall system health metrics."""
    uptime_seconds: float
    bays_connected: int
    bays_total: int
    total_detections: int
    system_load: float
    memory_usage_mb: float
    last_health_check: datetime

class HealthMonitor:
    """
    Comprehensive health monitoring for the car wash detection system.
    """
    
    def __init__(self):
        """Initialize the health monitor."""
        self.config = get_config()
        self.start_time = datetime.now()
        
        # Health tracking
        self.bay_healths: Dict[int, ConnectionHealth] = {}
        self.system_health = SystemHealth(
            uptime_seconds=0,
            bays_connected=0,
            bays_total=self.config.bay_count,
            total_detections=0,
            system_load=0.0,
            memory_usage_mb=0.0,
            last_health_check=datetime.now()
        )
        
        # Monitoring thread
        self.is_monitoring = False
        self.monitor_thread = None
        self.lock = threading.Lock()
        
        logger.info("Health monitor initialized")
    
    def start_monitoring(self):
        """Start the health monitoring thread."""
        if self.is_monitoring:
            logger.warning("Health monitor is already running")
            return
        
        self.is_monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        logger.info("Health monitoring started")
    
    def stop_monitoring(self):
        """Stop the health monitoring thread."""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1.0)
        
        logger.info("Health monitoring stopped")
    
    def update_bay_health(self, bay_id: int, processor_status: Dict):
        """Update health metrics for a specific bay."""
        with self.lock:
            current_time = datetime.now()
            
            # Calculate uptime percentage
            uptime_percentage = 0.0
            if processor_status.get('last_successful_connection'):
                total_time = (current_time - self.start_time).total_seconds()
                if total_time > 0:
                    # Rough estimate - could be improved with more detailed tracking
                    connection_time = total_time - (processor_status.get('total_reconnects', 0) * 30)  # Assume 30s downtime per reconnect
                    uptime_percentage = max(0, min(100, (connection_time / total_time) * 100))
            
            # Update bay health
            self.bay_healths[bay_id] = ConnectionHealth(
                bay_id=bay_id,
                is_connected=processor_status.get('is_connected', False),
                last_successful_connection=processor_status.get('last_successful_connection'),
                total_reconnects=processor_status.get('total_reconnects', 0),
                consecutive_failures=processor_status.get('consecutive_failures', 0),
                average_fps=processor_status.get('average_fps', 0.0),
                frames_processed=processor_status.get('frames_processed', 0),
                frames_failed=processor_status.get('frames_failed', 0),
                quality_level=processor_status.get('quality_level', 'unknown'),
                last_error=processor_status.get('last_error'),
                uptime_percentage=uptime_percentage
            )
    
    def get_bay_health(self, bay_id: int) -> Optional[ConnectionHealth]:
        """Get health metrics for a specific bay."""
        with self.lock:
            return self.bay_healths.get(bay_id)
    
    def get_system_health(self) -> SystemHealth:
        """Get overall system health metrics."""
        with self.lock:
            # Update system health
            current_time = datetime.now()
            self.system_health.uptime_seconds = (current_time - self.start_time).total_seconds()
            self.system_health.bays_connected = sum(1 for health in self.bay_healths.values() if health.is_connected)
            self.system_health.last_health_check = current_time
            
            return self.system_health
    
    def get_health_summary(self) -> Dict:
        """Get a comprehensive health summary."""
        with self.lock:
            system_health = self.get_system_health()
            
            # Bay summaries
            bay_summaries = {}
            for bay_id, health in self.bay_healths.items():
                bay_summaries[bay_id] = {
                    'connected': health.is_connected,
                    'uptime_percentage': health.uptime_percentage,
                    'total_reconnects': health.total_reconnects,
                    'quality_level': health.quality_level,
                    'fps': health.average_fps,
                    'frame_success_rate': (
                        (health.frames_processed / (health.frames_processed + health.frames_failed)) * 100
                        if (health.frames_processed + health.frames_failed) > 0 else 0
                    )
                }
            
            return {
                'system': asdict(system_health),
                'bays': bay_summaries,
                'alerts': self._get_health_alerts()
            }
    
    def _get_health_alerts(self) -> List[Dict]:
        """Get list of current health alerts."""
        alerts = []
        
        for bay_id, health in self.bay_healths.items():
            # Connection alerts
            if not health.is_connected:
                alerts.append({
                    'type': 'error',
                    'bay_id': bay_id,
                    'message': f"Bay {bay_id} is disconnected",
                    'severity': 'high'
                })
            
            # Quality degradation alerts
            if health.quality_level in ['medium', 'low']:
                alerts.append({
                    'type': 'warning',
                    'bay_id': bay_id,
                    'message': f"Bay {bay_id} running at {health.quality_level} quality",
                    'severity': 'medium'
                })
            
            # High reconnect rate alerts
            if health.total_reconnects > 10:
                alerts.append({
                    'type': 'warning',
                    'bay_id': bay_id,
                    'message': f"Bay {bay_id} has reconnected {health.total_reconnects} times",
                    'severity': 'medium'
                })
            
            # Low uptime alerts
            if health.uptime_percentage < 90:
                alerts.append({
                    'type': 'warning',
                    'bay_id': bay_id,
                    'message': f"Bay {bay_id} uptime is low ({health.uptime_percentage:.1f}%)",
                    'severity': 'medium'
                })
        
        return alerts
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.is_monitoring:
            try:
                # Log health summary periodically
                health_summary = self.get_health_summary()
                
                # Log system status
                system = health_summary['system']
                logger.info(f"📊 System Health: {system['bays_connected']}/{system['bays_total']} bays connected, "
                          f"uptime: {system['uptime_seconds']/3600:.1f}h")
                
                # Log bay status
                for bay_id, bay_health in health_summary['bays'].items():
                    status_emoji = "✅" if bay_health['connected'] else "❌"
                    logger.debug(f"{status_emoji} Bay {bay_id}: {bay_health['uptime_percentage']:.1f}% uptime, "
                               f"{bay_health['fps']:.1f} FPS, quality: {bay_health['quality_level']}")
                
                # Log alerts
                alerts = health_summary['alerts']
                if alerts:
                    logger.warning(f"🚨 Health alerts: {len(alerts)} issues detected")
                    for alert in alerts:
                        logger.warning(f"  {alert['type'].upper()}: {alert['message']}")
                
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {str(e)}")
            
            # Wait for next check
            time.sleep(self.config.health_check_interval)

# Global health monitor instance
health_monitor = HealthMonitor()

def get_health_monitor() -> HealthMonitor:
    """Get the global health monitor instance."""
    return health_monitor