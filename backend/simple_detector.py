import cv2
import numpy as np
import logging
from datetime import datetime, timedelta
from config import get_config

# Configure logging
logger = logging.getLogger('simple_detector')

class SimpleCarDetector:
    """
    Simple car detector optimized for overhead car wash bay cameras.
    Uses background subtraction instead of complex AI - much more reliable!
    """
    
    def __init__(self, bay_id=None):
        """
        Initialize the simple car detector with configuration-based settings.
        
        Args:
            bay_id: Bay identifier for loading pre-captured backgrounds
        """
        config = get_config()
        
        self.bay_id = bay_id
        self.learning_rate = config.detection.learning_rate
        self.min_contour_area = config.detection.min_contour_area
        self.bay_center_ratio = config.detection.bay_center_ratio
        self.confidence_threshold = config.detection.confidence_threshold
        self.learning_frames = config.detection.learning_frames
        self.confidence_change_threshold = config.detection.confidence_change_threshold
        self.empty_bay_log_interval = config.detection.empty_bay_log_interval
        
        # Background subtractor (learns empty bay background)
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            detectShadows=True,
            varThreshold=50,
            history=1000
        )
        
        # State tracking
        self.last_detection_time = None
        self.frame_count = 0
        self.is_learning = True
        self.background_loaded = False
        
        # Try to load pre-captured background
        if bay_id is not None:
            self.background_loaded = self.load_background(bay_id)
        
        logger.info("Simple car detector initialized")
    
    def load_background(self, bay_id):
        """
        Load pre-captured background image for instant detection.
        
        Args:
            bay_id: Bay identifier
            
        Returns:
            bool: True if background loaded successfully, False otherwise
        """
        import os
        
        try:
            # Try multiple possible locations for background images
            possible_paths = [
                f"backgrounds/bay_{bay_id}_background.jpg",  # From current working dir
                f"../backgrounds/bay_{bay_id}_background.jpg",  # From parent dir
                os.path.join(os.path.dirname(__file__), '..', 'backgrounds', f'bay_{bay_id}_background.jpg'),  # Relative to this file's parent
                os.path.join(os.path.dirname(__file__), 'backgrounds', f'bay_{bay_id}_background.jpg'),  # Same dir as this file
                os.path.join(os.getcwd(), 'backgrounds', f'bay_{bay_id}_background.jpg'),  # From current working directory
                os.path.join(os.getcwd(), '..', 'backgrounds', f'bay_{bay_id}_background.jpg')  # From parent of current working directory
            ]
            
            logger.info(f"Bay {bay_id}: Searching for background image...")
            
            background_path = None
            for path in possible_paths:
                abs_path = os.path.abspath(path)
                logger.info(f"Bay {bay_id}: Checking {abs_path}")
                
                if os.path.exists(abs_path):
                    background_path = abs_path
                    logger.info(f"Bay {bay_id}: ✅ Found background at {abs_path}")
                    break
                else:
                    logger.debug(f"Bay {bay_id}: ❌ Not found at {abs_path}")
            
            if background_path is None:
                logger.warning(f"Bay {bay_id}: ❌ No background image found in any of the expected locations")
                return False
            
            # Load the background image
            logger.info(f"Bay {bay_id}: Loading background image from {background_path}")
            background_image = cv2.imread(background_path)
            if background_image is None:
                logger.error(f"Bay {bay_id}: ❌ Failed to load background image from {background_path} (CV2 error)")
                return False
            
            # Log image details
            height, width = background_image.shape[:2]
            logger.info(f"Bay {bay_id}: Background image loaded - size: {width}x{height}")
            
            # Train the background subtractor with the pre-captured background
            # Apply the background multiple times to establish it as the base model
            logger.info(f"Bay {bay_id}: Training background subtractor...")
            for i in range(50):  # Apply multiple times to establish background
                self.bg_subtractor.apply(background_image, learningRate=0.9)
            
            # Set state to indicate background is ready
            self.is_learning = False
            self.frame_count = self.learning_frames  # Skip learning phase
            
            logger.info(f"✅ Bay {bay_id}: Background loaded successfully - ready for INSTANT detection!")
            return True
            
        except Exception as e:
            logger.error(f"Bay {bay_id}: ❌ Error loading background: {str(e)}")
            import traceback
            logger.error(f"Bay {bay_id}: Traceback: {traceback.format_exc()}")
            return False
    
    def detect_car(self, frame, bay_id=None):
        """
        Detect if a car is present in the bay.
        
        Args:
            frame: Camera frame
            bay_id: Bay identifier for logging
            
        Returns:
            (car_detected: bool, confidence: float)
        """
        if frame is None:
            return False, 0.0
        
        self.frame_count += 1
        bay_prefix = f"Bay {bay_id}: " if bay_id else ""
        
        # Apply background subtraction
        if self.background_loaded:
            # Use pre-loaded background - no learning needed
            fg_mask = self.bg_subtractor.apply(frame, learningRate=0.0)  # No learning
        else:
            # Learning mode - continue learning background
            fg_mask = self.bg_subtractor.apply(frame, learningRate=self.learning_rate)
            
            # Still learning background - no detections yet
            if self.frame_count < self.learning_frames:
                if self.frame_count % 20 == 0:  # Log progress every 20 frames
                    logger.info(f"{bay_prefix}Learning background... {self.frame_count}/{self.learning_frames}")
                return False, 0.0
        
        # Define region of interest (center area where cars park)
        height, width = fg_mask.shape
        center_margin_x = int(width * (1 - self.bay_center_ratio) / 2)
        center_margin_y = int(height * (1 - self.bay_center_ratio) / 2)
        
        # Extract center region
        roi = fg_mask[center_margin_y:height-center_margin_y, 
                     center_margin_x:width-center_margin_x]
        
        # Clean up the mask (remove noise)
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        roi = cv2.morphologyEx(roi, cv2.MORPH_OPEN, kernel)
        roi = cv2.morphologyEx(roi, cv2.MORPH_CLOSE, kernel)
        
        # Find contours (objects) in the center area
        contours, _ = cv2.findContours(roi, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Check if any significant objects detected
        significant_contours = []
        total_area = 0
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > self.min_contour_area:
                significant_contours.append(contour)
                total_area += area
        
        # Calculate confidence based on area coverage
        roi_area = roi.shape[0] * roi.shape[1]
        coverage_ratio = total_area / roi_area if roi_area > 0 else 0
        confidence = min(coverage_ratio * 2, 1.0)  # Scale to 0-1 range
        
        # Detect car if significant objects found
        car_detected = len(significant_contours) > 0 and confidence > self.confidence_threshold
        
        if car_detected:
            # Only log significant confidence changes to reduce spam
            if not hasattr(self, '_last_logged_confidence') or abs(confidence - self._last_logged_confidence) > self.confidence_change_threshold:
                logger.info(f"{bay_prefix}🚗 Car detected! Confidence: {confidence:.2f}")
                self._last_logged_confidence = confidence
            self.last_detection_time = datetime.now()
        else:
            # Only log occasionally to avoid spam
            if self.frame_count % self.empty_bay_log_interval == 0:
                logger.debug(f"{bay_prefix}Bay empty (conf: {confidence:.2f})")
            self._last_logged_confidence = 0.0
        
        return car_detected, confidence
    
    def reset_background(self):
        """Reset the background model (call when bay is known to be empty)"""
        logger.info("Resetting background model")
        self.bg_subtractor = cv2.createBackgroundSubtractorMOG2(
            detectShadows=True,
            varThreshold=50,
            history=1000
        )
        self.frame_count = 0
        self.is_learning = True
    
    def get_debug_frame(self, frame):
        """Get a debug frame showing the detection area and mask"""
        if frame is None:
            return None
        
        # Create debug visualization
        debug_frame = frame.copy()
        height, width = frame.shape[:2]
        
        # Draw ROI rectangle
        center_margin_x = int(width * (1 - self.bay_center_ratio) / 2)
        center_margin_y = int(height * (1 - self.bay_center_ratio) / 2)
        
        cv2.rectangle(debug_frame, 
                     (center_margin_x, center_margin_y),
                     (width - center_margin_x, height - center_margin_y),
                     (0, 255, 0), 2)
        
        # Add status text
        status = "LEARNING" if self.frame_count < self.learning_frames else "ACTIVE"
        cv2.putText(debug_frame, f"Status: {status}", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        return debug_frame