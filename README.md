# Car Wash Bay Status App

This project consists of a Flutter mobile app and a Python backend that work together to provide real-time status information about car wash bays. The system uses YOLOv4 object detection with RTSP camera streams to determine if a bay is in use or available.

## System Architecture

The system is divided into two main components:

1. **Backend (Python + Flask)**
   - YOLOv4 object detection for vehicle detection
   - RTSP stream processing
   - RESTful API with JWT authentication
   - Admin dashboard for monitoring

2. **Frontend (Flutter)**
   - Cross-platform mobile app
   - Real-time bay status display
   - Authentication system
   - Multilingual support (English/Swedish)

## Backend

The backend is built with Python and Flask, using OpenCV for computer vision tasks. It processes RTSP video streams from cameras at each car wash bay, detects vehicles using YOLOv4, and provides this information through a RESTful API.

### Key Features

- **Vehicle Detection**: Uses YOLOv4-CSP model to detect vehicles in RTSP streams
- **Bay Status Tracking**: Maintains the current status of each bay (Available, In Use, Out of Service)
- **Error Handling**: Robust error handling for RTSP stream disconnections
- **Authentication**: JWT-based authentication for API security
- **Admin Dashboard**: Web interface for monitoring system status

### Setup

1. Install dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. Configure environment variables in `.env` file

3. Run the server:
   ```bash
   python run_server.py
   ```
   
   The script provides several options:
   ```
   python run_server.py --help
   ```

## Frontend

The frontend is a Flutter mobile app that displays the status of each car wash bay in real-time. It communicates with the backend API to fetch bay statuses and provides a user-friendly interface for customers.

### Key Features

- **Real-time Status**: Shows the current status of each bay
- **Authentication**: Login and registration system
- **Multilingual**: Supports English and Swedish
- **Responsive Design**: Works on various device sizes

### Setup

1. Install dependencies:
   ```bash
   flutter pub get
   ```

2. Configure the API URL:
   ```bash
   python update_api_url.py http://your-server-ip:5000/api
   ```

3. Run the app:
   ```bash
   flutter run
   ```

## API Endpoints

- `POST /api/auth/register` - Register a new user
- `POST /api/auth/login` - Login and get JWT token
- `GET /api/stations` - Get status of all bays (requires JWT)
- `GET /api/guest/stations` - Get status of all bays (guest mode, no authentication)
- `GET /api/health` - Health check endpoint

## RTSP Streams

The system is configured to work with the following RTSP streams:

- Bay 1: `rtsp://192.168.1.74:7447/VJ1fB8D4d03nIwKF`
- Bay 2: `rtsp://192.168.1.74:7447/zfDlcWJLTq10A49M`
- Bay 3: `rtsp://192.168.1.74:7447/18JUhav6VfoOMVS0`
- Bay 4: `rtsp://192.168.1.74:7447/BSPtMFwAXLncNdx0`

## Security Notes

For production deployment:
1. Change default admin credentials
2. Set strong secret keys for JWT
3. Implement HTTPS
4. Store user credentials securely (current implementation uses plaintext)
