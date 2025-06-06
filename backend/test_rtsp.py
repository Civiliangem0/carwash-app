#!/usr/bin/env python3
"""
Script to test RTSP streams.
"""
import os
import sys
import argparse
import time
import cv2
from dotenv import load_dotenv

def test_rtsp_stream(rtsp_url, save_frame=False, output_dir=None, timeout=10):
    """Test an RTSP stream by connecting and capturing frames."""
    print(f"Testing RTSP stream: {rtsp_url}")
    
    # Create output directory if needed
    if save_frame and output_dir:
        os.makedirs(output_dir, exist_ok=True)
    
    # Open RTSP stream
    cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
    
    if not cap.isOpened():
        print("Error: Could not open RTSP stream")
        return False
    
    print("Successfully connected to RTSP stream")
    
    # Set buffer size
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    
    # Try to read frames
    start_time = time.time()
    frame_count = 0
    last_frame = None
    
    while time.time() - start_time < timeout:
        ret, frame = cap.read()
        
        if not ret:
            print("Warning: Failed to read frame")
            time.sleep(0.5)
            continue
        
        frame_count += 1
        last_frame = frame
        
        # Print frame info every 10 frames
        if frame_count % 10 == 0:
            print(f"Received {frame_count} frames, resolution: {frame.shape[1]}x{frame.shape[0]}")
    
    # Release the capture
    cap.release()
    
    if frame_count == 0:
        print("Error: No frames received")
        return False
    
    print(f"Successfully received {frame_count} frames in {time.time() - start_time:.1f} seconds")
    
    # Save the last frame if requested
    if save_frame and last_frame is not None and output_dir:
        # Generate filename from RTSP URL
        filename = rtsp_url.split('/')[-1]
        if not filename:
            filename = "rtsp_frame"
        
        output_path = os.path.join(output_dir, f"{filename}.jpg")
        cv2.imwrite(output_path, last_frame)
        print(f"Saved frame to: {output_path}")
    
    return True

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test RTSP streams")
    parser.add_argument("--url", help="RTSP URL to test")
    parser.add_argument("--bay", type=int, choices=[1, 2, 3, 4], help="Bay number to test (1-4)")
    parser.add_argument("--all", action="store_true", help="Test all configured RTSP streams")
    parser.add_argument("--save", action="store_true", help="Save a frame from the stream")
    parser.add_argument("--output-dir", default="rtsp_frames", help="Directory to save frames")
    parser.add_argument("--timeout", type=int, default=10, help="Timeout in seconds")
    
    args = parser.parse_args()
    
    # Change to the script's directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Load environment variables
    load_dotenv()
    
    # Check arguments
    if not (args.url or args.bay or args.all):
        parser.error("Please specify --url, --bay, or --all")
    
    success = True
    
    # Test specific URL
    if args.url:
        success = test_rtsp_stream(args.url, args.save, args.output_dir, args.timeout)
    
    # Test specific bay
    elif args.bay:
        rtsp_url = os.environ.get(f"RTSP_URL_{args.bay}")
        if not rtsp_url:
            print(f"Error: RTSP URL for Bay {args.bay} not found in environment variables")
            return 1
        
        success = test_rtsp_stream(rtsp_url, args.save, args.output_dir, args.timeout)
    
    # Test all bays
    elif args.all:
        for bay in range(1, 5):
            rtsp_url = os.environ.get(f"RTSP_URL_{bay}")
            if not rtsp_url:
                print(f"Error: RTSP URL for Bay {bay} not found in environment variables")
                success = False
                continue
            
            bay_success = test_rtsp_stream(rtsp_url, args.save, args.output_dir, args.timeout)
            success = success and bay_success
            
            # Add a separator between bays
            if bay < 4:
                print("\n" + "-" * 40 + "\n")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
