import cv2
import numpy as np
import logging
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger('simple_detector')

class SimpleCarDetector:
    """
    Simple car detector optimized for overhead car wash bay cameras.
    Uses background subtraction instead of complex AI - much more reliable!
    """
    
    def __init__(self, learning_rate=0.001, min_contour_area=2000, bay_center_ratio=0.4):
        """
        Initialize the simple car detector.
        
        Args:
            learning_rate: How fast to adapt to lighting changes (0.001 = very slow)
            min_contour_area: Minimum area for detected objects (pixels)
            bay_center_ratio: What ratio of the frame center to check (0.4 = 40% of center)
        """
        self.learning_rate = learning_rate
        self.min_contour_area = min_contour_area
        self.bay_center_ratio = bay_center_ratio
        
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
        self.learning_frames = 100  # Learn background for first 100 frames
        
        logger.info("Simple car detector initialized")
    
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
        car_detected = len(significant_contours) > 0 and confidence > 0.1
        
        if car_detected:
            logger.info(f"{bay_prefix}🚗 Car detected! Confidence: {confidence:.2f}, "
                       f"Objects: {len(significant_contours)}, Area: {total_area}")
            self.last_detection_time = datetime.now()
        else:
            # Only log occasionally to avoid spam
            if self.frame_count % 50 == 0:
                logger.debug(f"{bay_prefix}Bay empty (conf: {confidence:.2f})")
        
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