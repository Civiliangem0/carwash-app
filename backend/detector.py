import cv2
import numpy as np
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Enable debug logging
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('detector')

class VehicleDetector:
    """
    Class for detecting vehicles in images using YOLOv4 model.
    """
    # Vehicle-related class IDs in COCO dataset - Only cars for car wash detection
    VEHICLE_CLASSES = [2]  # car only (removing motorbike, bus, train, truck, boat)
    
    def __init__(self, config_path, weights_path, names_path, 
                 confidence_threshold=0.4, nms_threshold=0.4, 
                 min_box_area=1000, max_box_area_ratio=0.9):
        """
        Initialize the vehicle detector with YOLOv4 model.
        
        Args:
            config_path: Path to YOLOv4 config file
            weights_path: Path to YOLOv4 weights file
            names_path: Path to COCO names file
            confidence_threshold: Minimum confidence for detection (increased to 0.7)
            nms_threshold: Non-maximum suppression threshold
            min_box_area: Minimum bounding box area (pixels) to consider as vehicle
            max_box_area_ratio: Maximum ratio of box area to frame area
        """
        self.confidence_threshold = confidence_threshold
        self.nms_threshold = nms_threshold
        self.min_box_area = min_box_area
        self.max_box_area_ratio = max_box_area_ratio
        
        # Check if model files exist
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Config file not found: {config_path}")
        if not os.path.exists(weights_path):
            raise FileNotFoundError(f"Weights file not found: {weights_path}")
        if not os.path.exists(names_path):
            raise FileNotFoundError(f"Names file not found: {names_path}")
        
        # Load class names
        with open(names_path, 'r') as f:
            self.classes = [line.strip() for line in f.readlines()]
        
        # Load YOLOv4 network
        logger.info(f"Loading YOLOv4 model from {weights_path} and {config_path}")
        self.net = cv2.dnn.readNetFromDarknet(config_path, weights_path)
        
        # Set preferred backend and target
        self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_CUDA)
        self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CUDA)
        
        # Get output layer names
        layer_names = self.net.getLayerNames()
        self.output_layers = [layer_names[i - 1] for i in self.net.getUnconnectedOutLayers()]
        
        logger.info("YOLOv4 model loaded successfully")
        
    def detect_vehicles(self, frame, bay_id=None):
        """
        Detect vehicles in a frame.
        
        Args:
            frame: Image frame from video stream
            bay_id: Optional bay ID for logging purposes
            
        Returns:
            detected: Boolean indicating if any vehicle was detected
            detections: List of detection results (class_id, confidence, bbox)
            processed_frame: Frame with detection boxes (if draw=True)
        """
        if frame is None:
            logger.warning("Received empty frame for detection")
            return False, []
        
        height, width, _ = frame.shape
        
        # Create blob from image
        blob = cv2.dnn.blobFromImage(frame, 1/255.0, (416, 416), swapRB=True, crop=False)
        
        # Set input and forward pass
        self.net.setInput(blob)
        outputs = self.net.forward(self.output_layers)
        
        # Process outputs
        class_ids = []
        confidences = []
        boxes = []
        
        frame_area = height * width
        
        for output in outputs:
            for detection in output:
                # YOLO format: [center_x, center_y, width, height, objectness, class1_prob, class2_prob, ...]
                center_x = detection[0]
                center_y = detection[1]
                width_norm = detection[2]
                height_norm = detection[3]
                objectness = detection[4]
                scores = detection[5:]
                
                class_id = np.argmax(scores)
                class_prob = scores[class_id]
                
                # Final confidence is objectness * class_probability
                confidence = objectness * class_prob
                
                # Debug: Log only high-confidence car detections to reduce spam
                if class_id in self.VEHICLE_CLASSES and confidence > 0.5:
                    bay_prefix = f"Bay {bay_id}: " if bay_id else ""
                    logger.debug(f"{bay_prefix}Car candidate - confidence: {confidence:.3f}")
                
                # Filter for vehicle classes and confidence threshold
                if class_id in self.VEHICLE_CLASSES and confidence > self.confidence_threshold:
                    # Convert normalized coordinates to pixel coordinates
                    center_x_px = int(center_x * width)
                    center_y_px = int(center_y * height)
                    w = int(width_norm * width)
                    h = int(height_norm * height)
                    
                    # Calculate bounding box area
                    box_area = w * h
                    box_area_ratio = box_area / frame_area
                    
                    # Apply size filters to reduce false positives
                    # Note: Cars appear as thin slices from camera angle, so relaxed height requirement
                    if (box_area >= self.min_box_area and 
                        box_area_ratio <= self.max_box_area_ratio and
                        w > 30):  # Only require minimum width, height can be small due to camera angle
                        
                        # Rectangle coordinates
                        x = int(center_x_px - w / 2)
                        y = int(center_y_px - h / 2)
                        
                        # Ensure bounding box is within frame boundaries
                        x = max(0, min(x, width - w))
                        y = max(0, min(y, height - h))
                        
                        boxes.append([x, y, w, h])
                        confidences.append(float(confidence))
                        class_ids.append(class_id)
                        
                        bay_prefix = f"Bay {bay_id}: " if bay_id else ""
                        logger.info(f"{bay_prefix}✅ VALID CAR: confidence={confidence:.3f}")
                    else:
                        # Only log filtered detections if they have high confidence (reduce spam)
                        if confidence > 0.5:
                            reasons = []
                            if box_area < self.min_box_area:
                                reasons.append(f"area too small ({box_area} < {self.min_box_area})")
                            if box_area_ratio > self.max_box_area_ratio:
                                reasons.append(f"area ratio too large ({box_area_ratio:.3f} > {self.max_box_area_ratio})")
                            if w <= 30:
                                reasons.append(f"width too small ({w} <= 30)")
                            
                            bay_prefix = f"Bay {bay_id}: " if bay_id else ""
                            logger.debug(f"{bay_prefix}❌ FILTERED: {', '.join(reasons)}")
        
        # Apply non-maximum suppression
        indices = cv2.dnn.NMSBoxes(boxes, confidences, self.confidence_threshold, self.nms_threshold)
        
        # Prepare results
        detections = []
        for i in indices:
            if isinstance(i, list):  # OpenCV 4.5.4 and earlier returns a list
                i = i[0]
            box = boxes[i]
            class_id = class_ids[i]
            confidence = confidences[i]
            detections.append({
                'class_id': class_id,
                'class_name': self.classes[class_id],
                'confidence': confidence,
                'box': box
            })
        
        # Log detection summary (only for positive detections to reduce spam)
        if len(detections) > 0:
            bay_prefix = f"Bay {bay_id}: " if bay_id else ""
            logger.info(f"{bay_prefix}🚗 Detected {len(detections)} cars")
        else:
            # Only log "no vehicles" occasionally to reduce spam
            bay_prefix = f"Bay {bay_id}: " if bay_id else ""
            logger.debug(f"{bay_prefix}No cars detected")
        
        # Return whether any vehicle was detected and the detections
        return len(detections) > 0, detections
    
    def draw_detections(self, frame, detections):
        """
        Draw detection boxes on the frame.
        
        Args:
            frame: Original image frame
            detections: List of detection results
            
        Returns:
            frame: Frame with detection boxes drawn
        """
        for detection in detections:
            x, y, w, h = detection['box']
            label = f"{detection['class_name']}: {detection['confidence']:.2f}"
            
            # Draw bounding box
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            # Draw label
            cv2.putText(frame, label, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        return frame
