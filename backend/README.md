# Car Wash Bay Status Backend

This backend system uses YOLOv4 object detection with OpenCV to monitor car wash bays through RTSP camera streams. It provides a Flask API for the Flutter app to get real-time bay availability status.

## Features

- Real-time vehicle detection using YOLOv4
- RTSP stream processing with error handling and reconnection
- RESTful API with JWT authentication
- Admin dashboard for system monitoring
- Bay status tracking with configurable thresholds

## Requirements

- Python 3.8+
- OpenCV with CUDA support (for optimal performance)
- Flask and related packages
- YOLOv4-CSP model files

## Installation

1. Install the required Python packages:

```bash
pip install -r requirements.txt
```

2. Make sure the YOLOv4 model files are in the correct location:
   - `yolov4/yolov4-csp.cfg`
   - `yolov4/yolov4-csp.weights`

3. Configure the environment variables in the `.env` file:
   - RTSP stream URLs
   - Detection parameters
   - Authentication secrets

## Running the Server

Start the Flask server:

```bash
python app.py
```

The server will:
1. Load the YOLOv4 model
2. Connect to the RTSP streams
3. Start processing frames to detect vehicles
4. Expose the API endpoints

## API Endpoints

### Authentication

- `POST /api/auth/register` - Register a new user
- `POST /api/auth/login` - Login and get JWT token

### Bay Status

- `GET /api/stations` - Get status of all bays (requires JWT)
- `GET /api/guest/stations` - Get status of all bays (guest mode, no authentication)

### Admin

- `GET /admin` - Admin dashboard (requires admin login)
- `GET /api/admin/bays` - Get detailed bay status (requires admin login)
- `GET /api/health` - Health check endpoint

## Utility Scripts

### run_server.py

Run the Flask server with various options:

```bash
python run_server.py --help
```

### test_yolo.py

Test the YOLOv4 model with a single image:

```bash
python test_yolo.py path/to/image.jpg
```

This script will:
1. Load the YOLOv4 model
2. Detect vehicles in the image
3. Draw bounding boxes around detected vehicles
4. Save the output image with "_detected" suffix

### test_rtsp.py

Test RTSP stream connectivity:

```bash
# Test a specific bay
python test_rtsp.py --bay 1

# Test all bays
python test_rtsp.py --all

# Test a specific URL and save a frame
python test_rtsp.py --url rtsp://example.com/stream --save
```

This script will:
1. Connect to the RTSP stream
2. Capture frames for a specified duration
3. Report success/failure and stream information
4. Optionally save a captured frame

### test_api.py

Test the API endpoints:

```bash
# Test all endpoints
python test_api.py --all

# Test specific endpoints
python test_api.py --register --login --stations --health

# Test with custom credentials
python test_api.py --username admin --password secure123 --login
```

This script will:
1. Register a new user (if requested)
2. Login and get a JWT token
3. Retrieve bay statuses
4. Perform a health check

## Configuration

The system can be configured through environment variables in the `.env` file:

- `PORT` - Server port (default: 5000)
- `RTSP_URL_1` to `RTSP_URL_4` - RTSP stream URLs for each bay
- `CONFIDENCE_THRESHOLD` - Minimum confidence for vehicle detection
- `STATUS_CHANGE_THRESHOLD` - Number of consecutive detections needed to change status

## Admin Dashboard

Access the admin dashboard at `/admin` with the default credentials:
- Username: admin
- Password: admin123

The dashboard provides:
- Real-time bay status monitoring
- Connection status for each camera
- Detection confidence levels
- System uptime information

## Security Notes

For production deployment:
1. Change the default admin credentials
2. Set strong secret keys for JWT and session encryption
3. Consider implementing HTTPS
4. Store user credentials securely (current implementation uses plaintext)
