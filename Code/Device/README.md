# Pothole Detection System - Raspberry Pi Device

This directory contains the Raspberry Pi implementation of the pothole detection system using a custom YOLOv8n + CBAM model.

## System Overview

The system integrates multiple sensors and components:

- **Camera**: Pi Camera for visual pothole detection using YOLOv8n + CBAM model
- **Ultrasonic Sensor**: HC-SR04 for distance measurement
- **Vibration Sensor**: SW-420 for impact detection
- **GPS Module**: For location tracking
- **Speaker**: Audio notifications
- **LED Display**: Visual status indicators
- **Backend Upload**: Automatic data upload to government server

## Hardware Setup

### Required Components

1. **Raspberry Pi 4B** (recommended) or Pi 3B+
2. **Pi Camera Module** (v2 or higher)
3. **HC-SR04 Ultrasonic Sensor**
4. **SW-420 Vibration Sensor**
5. **GPS Module** (UART interface)
6. **Speaker** (3.5mm or USB)
7. **LEDs** (4x for status indication)
8. **Resistors** (220Ω for LEDs)
9. **Breadboard and jumper wires**

### GPIO Pin Configuration

| Component | GPIO Pin | Purpose |
|-----------|----------|---------|
| Ultrasonic Trigger | GPIO 18 | HC-SR04 trigger |
| Ultrasonic Echo | GPIO 24 | HC-SR04 echo |
| Vibration Sensor | GPIO 23 | SW-420 output |
| System Ready LED | GPIO 25 | Green LED |
| System Error LED | GPIO 22 | Red LED |
| GPS Status LED | GPIO 27 | Blue LED |
| Detection LED | GPIO 17 | Yellow LED |

### Wiring Diagram

```
Raspberry Pi GPIO Layout:
                   3V3  (1) (2)  5V
                 GPIO2  (3) (4)  5V
                 GPIO3  (5) (6)  GND
                 GPIO4  (7) (8)  GPIO14
                   GND  (9) (10) GPIO15
                GPIO17 (11) (12) GPIO18
                GPIO27 (13) (14) GND
                GPIO22 (15) (16) GPIO23
                   3V3 (17) (18) GPIO24
                GPIO10 (19) (20) GND
                 GPIO9 (21) (22) GPIO25
                GPIO11 (23) (24) GPIO8
                   GND (25) (26) GPIO7
```

## Installation

### 1. System Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Enable camera interface
sudo raspi-config
# Navigate to Interface Options > Camera > Enable

# Enable UART for GPS
sudo raspi-config
# Navigate to Interface Options > Serial Port > Enable

# Install Python dependencies
sudo apt install python3-pip python3-venv python3-dev
sudo apt install libhdf5-dev libhdf5-serial-dev libhdf5-103
sudo apt install libqtgui4 libqtwebkit4 libqt4-test python3-pyqt5
sudo apt install libatlas-base-dev libjasper-dev libqtgui4
```

### 2. Python Environment

```bash
# Create virtual environment
python3 -m venv pothole_env
source pothole_env/bin/activate

# Install requirements
pip install -r requirements.txt

# For PyTorch on Raspberry Pi (CPU only)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

### 3. Model Setup

```bash
# Create models directory
mkdir -p models

# Copy your trained YOLOv8n + CBAM model
cp /path/to/your/yolov8n_cbam_pothole.pt models/

# Verify model file
ls -la models/
```

### 4. Configuration

```bash
# Generate default configuration
python3 config.py

# Edit configuration if needed
nano config.json
```

## Usage

### Basic Usage

```bash
# Activate environment
source pothole_env/bin/activate

# Run the system
python3 main.py
```

### Configuration Options

Edit `config.json` to customize:

- **Model settings**: Confidence threshold, IoU threshold
- **Camera settings**: Resolution, FPS, detection interval
- **Sensor settings**: GPIO pins, thresholds
- **Backend settings**: Server URL, API key, device ID
- **Notification settings**: Audio, display preferences

### Environment Variables

You can also configure using environment variables:

```bash
export MODEL_PATH="models/yolov8n_cbam_pothole.pt"
export DETECTION_CONFIDENCE="0.25"
export BACKEND_URL="http://192.168.0.3:8080"
export BACKEND_USERNAME="pappuraj.duet@gmail.com"
export BACKEND_PASSWORD="11223344"
export DEVICE_ID="pothole_detector_001"
```

## System Components

### Main Controller (`main.py`)
- Orchestrates all system components
- Manages detection loop and sensor monitoring
- Handles pothole detection events

### Pothole Detector (`pothole_detector.py`)
- Loads and runs YOLOv8n + CBAM model
- Handles camera capture and inference
- Saves detection images with annotations

### Sensor Manager (`sensor_manager.py`)
- Manages ultrasonic, vibration, and GPS sensors
- Monitors sensor readings continuously
- Detects pothole indicators from sensors

### Notification System (`notification_system.py`)
- Handles audio and visual notifications
- Manages LED status indicators
- Provides user feedback for detections

### Backend Client (`backend_client.py`)
- Uploads detection data to government server
- Handles offline storage when network unavailable
- Manages upload queue and retry logic

### Configuration (`config.py`)
- Centralized configuration management
- Environment variable support
- Configuration validation

## Data Flow

1. **Continuous Monitoring**: Sensors monitor road conditions
2. **Trigger Detection**: Vibration or ultrasonic sensors trigger camera
3. **Visual Analysis**: YOLOv8n + CBAM model analyzes camera frame
4. **Confirmation**: Multiple sensors confirm pothole presence
5. **Notification**: Audio/visual alerts notify user
6. **Data Upload**: Detection data uploaded to backend server
7. **Storage**: Images and metadata saved locally

## Troubleshooting

### Common Issues

1. **Camera not detected**:
   ```bash
   # Check camera connection
   libcamera-hello --list-cameras
   # Enable camera in raspi-config
   ```

2. **GPIO permission denied**:
   ```bash
   # Add user to gpio group
   sudo usermod -a -G gpio $USER
   # Reboot required
   ```

3. **Model loading errors**:
   ```bash
   # Check model file exists and is readable
   ls -la models/yolov8n_cbam_pothole.pt
   # Verify file integrity
   ```

4. **GPS not working**:
   ```bash
   # Check UART is enabled
   sudo raspi-config
   # Test GPS connection
   cat /dev/ttyUSB0
   ```

5. **Backend upload failures**:
   ```bash
   # Check network connectivity
   ping 192.168.0.3
   # Test backend connection
   python3 test_backend.py
   # Verify username/password and URL
   ```

### Logs

System logs are written to:
- `pothole_system.log` - Main system log
- `detections/` - Detection images and metadata
- `offline_detections/` - Offline storage for failed uploads

### Performance Optimization

For better performance on Raspberry Pi:

1. **Reduce camera resolution** if needed
2. **Increase detection interval** to process fewer frames
3. **Use CPU-only PyTorch** (no GPU acceleration)
4. **Close unnecessary services** to free resources

## Development

### Adding New Sensors

1. Extend `SensorManager` class
2. Add GPIO pin configuration
3. Implement reading methods
4. Update pothole indicator logic

### Customizing Notifications

1. Modify `NotificationSystem` class
2. Add new LED patterns or sounds
3. Implement custom notification logic

### Backend Integration

The system is configured to work with your Spring Security JWT backend:

- **Server**: `http://192.168.0.3:8080`
- **Username**: `pappuraj.duet@gmail.com`
- **Password**: `11223344`
- **Authentication**: JWT tokens via `/api/auth/login`

#### Authentication Flow:

1. **Device Startup**: System authenticates with backend using username/password
2. **Token Storage**: JWT tokens are saved to `tokens.json` file
3. **API Calls**: All subsequent API calls use the saved JWT token
4. **Token Refresh**: Automatically refreshes tokens before expiration
5. **Re-authentication**: Falls back to login if refresh fails

#### API Endpoints: 
  - `POST /api/auth/login` - Initial authentication (username/password)
  - `POST /api/auth/refresh` - Refresh access token
  - `POST /api/detections` - Upload detection data (with JWT token)
  - `POST /api/detections/{id}/image` - Upload detection images (with JWT token)
  - `GET /api/health` - Health check (with JWT token)

**Test Backend Connection**:
```bash
python3 test_backend.py
```

**Backend Configuration**:
```json
{
  "backend_url": "http://192.168.0.3:8080",
  "backend_username": "pappuraj.duet@gmail.com", 
  "backend_password": "11223344",
  "device_id": "pothole_detector_001"
}
```

**Environment Variables for Backend**:
```bash
export BACKEND_URL="http://192.168.0.3:8080"
export BACKEND_USERNAME="pappuraj.duet@gmail.com"
export BACKEND_PASSWORD="11223344"
export DEVICE_ID="pothole_detector_001"
```

## License

This project is part of the pothole detection system for government use.

## Support

For technical support or issues:
1. Check logs for error messages
2. Verify hardware connections
3. Test individual components
4. Contact system administrator
