#!/usr/bin/env python3
"""
Script to test the YOLOv4 model with a single image.
"""
import os
import sys
import argparse
import cv2
import numpy as np
from detector import VehicleDetector

def test_yolo_with_image(image_path, config_path, weights_path, names_path, confidence=0.5):
    """Test YOLOv4 model with a single image."""
    # Check if image exists
    if not os.path.exists(image_path):
        print(f"Error: Image not found: {image_path}")
        return False
    
    # Check if model files exist
    if not os.path.exists(config_path):
        print(f"Error: Config file not found: {config_path}")
        return False
    if not os.path.exists(weights_path):
        print(f"Error: Weights file not found: {weights_path}")
        return False
    if not os.path.exists(names_path):
        print(f"Error: Names file not found: {names_path}")
        return False
    
    try:
        # Load image
        image = cv2.imread(image_path)
        if image is None:
            print(f"Error: Could not load image: {image_path}")
            return False
        
        # Initialize detector
        print("Initializing YOLOv4 detector...")
        detector = VehicleDetector(
            config_path=config_path,
            weights_path=weights_path,
            names_path=names_path,
            confidence_threshold=confidence
        )
        
        # Detect vehicles
        print("Detecting vehicles...")
        detected, detections = detector.detect_vehicles(image)
        
        # Draw detections
        if detected:
            print(f"Detected {len(detections)} vehicles:")
            for i, detection in enumerate(detections):
                print(f"  {i+1}. {detection['class_name']} - Confidence: {detection['confidence']:.2f}")
            
            # Draw bounding boxes
            image_with_boxes = detector.draw_detections(image.copy(), detections)
            
            # Save output image
            output_path = os.path.splitext(image_path)[0] + "_detected" + os.path.splitext(image_path)[1]
            cv2.imwrite(output_path, image_with_boxes)
            print(f"Output image saved to: {output_path}")
        else:
            print("No vehicles detected in the image.")
        
        return True
        
    except Exception as e:
        print(f"Error testing YOLOv4 model: {str(e)}")
        return False

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test YOLOv4 model with a single image")
    parser.add_argument("image_path", help="Path to the image file")
    parser.add_argument("--config", default="../yolov4/yolov4-csp.cfg", help="Path to YOLOv4 config file")
    parser.add_argument("--weights", default="../yolov4/yolov4-csp.weights", help="Path to YOLOv4 weights file")
    parser.add_argument("--names", default="coco.names", help="Path to COCO names file")
    parser.add_argument("--confidence", type=float, default=0.5, help="Confidence threshold (0.0-1.0)")
    
    args = parser.parse_args()
    
    # Change to the script's directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    if not test_yolo_with_image(
        args.image_path,
        args.config,
        args.weights,
        args.names,
        args.confidence
    ):
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
