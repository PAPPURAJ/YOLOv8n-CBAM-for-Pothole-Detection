#!/bin/bash
# Setup script for Pothole Detection System on Raspberry Pi

set -e  # Exit on any error

echo "=== Pothole Detection System Setup ==="
echo "This script will set up the pothole detection system on Raspberry Pi"
echo

# Check if running on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo "Warning: This script is designed for Raspberry Pi"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Update system
echo "Updating system packages..."
sudo apt update
sudo apt upgrade -y

# Install system dependencies
echo "Installing system dependencies..."
sudo apt install -y \
    python3-pip \
    python3-venv \
    python3-dev \
    python3-numpy \
    python3-opencv \
    libhdf5-dev \
    libhdf5-serial-dev \
    libhdf5-103 \
    libqtgui4 \
    libqtwebkit4 \
    libqt4-test \
    python3-pyqt5 \
    libatlas-base-dev \
    libjasper-dev \
    libqtgui4 \
    git \
    wget \
    curl \
    vim \
    htop \
    i2c-tools \
    libi2c-dev

# Enable required interfaces
echo "Enabling required interfaces..."

# Enable camera
if ! grep -q "start_x=1" /boot/config.txt; then
    echo "start_x=1" | sudo tee -a /boot/config.txt
fi

if ! grep -q "gpu_mem=128" /boot/config.txt; then
    echo "gpu_mem=128" | sudo tee -a /boot/config.txt
fi

# Enable UART for GPS
if ! grep -q "enable_uart=1" /boot/config.txt; then
    echo "enable_uart=1" | sudo tee -a /boot/config.txt
fi

# Enable I2C (optional for future sensors)
if ! grep -q "dtparam=i2c_arm=on" /boot/config.txt; then
    echo "dtparam=i2c_arm=on" | sudo tee -a /boot/config.txt
fi

# Enable SPI (optional for future sensors)
if ! grep -q "dtparam=spi=on" /boot/config.txt; then
    echo "dtparam=spi=on" | sudo tee -a /boot/config.txt
fi

# Add user to required groups
echo "Adding user to required groups..."
sudo usermod -a -G gpio,i2c,spi $USER

# Create virtual environment
echo "Creating Python virtual environment..."
python3 -m venv pothole_env
source pothole_env/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Install PyTorch for Raspberry Pi (CPU only)
echo "Installing PyTorch for Raspberry Pi..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Create necessary directories
echo "Creating system directories..."
mkdir -p models
mkdir -p detections
mkdir -p offline_detections
mkdir -p logs
mkdir -p sounds

# Generate default configuration
echo "Generating default configuration..."
python3 config.py

# Set up systemd service (optional)
echo "Setting up systemd service..."
sudo tee /etc/systemd/system/pothole-detector.service > /dev/null << EOF
[Unit]
Description=Pothole Detection System
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment=PATH=$(pwd)/pothole_env/bin
ExecStart=$(pwd)/pothole_env/bin/python3 main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable service (but don't start yet)
sudo systemctl daemon-reload
sudo systemctl enable pothole-detector.service

# Create startup script
echo "Creating startup script..."
cat > start_pothole_system.sh << 'EOF'
#!/bin/bash
# Startup script for Pothole Detection System

cd "$(dirname "$0")"
source pothole_env/bin/activate

echo "Starting Pothole Detection System..."
echo "Press Ctrl+C to stop"

python3 main.py
EOF

chmod +x start_pothole_system.sh

# Create system info script
echo "Creating system info script..."
cat > system_info.py << 'EOF'
#!/usr/bin/env python3
"""System information and diagnostics"""

import sys
import platform
import subprocess
import os
from pathlib import Path

def get_system_info():
    """Get system information"""
    info = {}
    
    # Basic system info
    info['platform'] = platform.platform()
    info['python_version'] = sys.version
    info['architecture'] = platform.architecture()
    
    # Raspberry Pi specific
    try:
        with open('/proc/device-tree/model', 'r') as f:
            info['device_model'] = f.read().strip()
    except:
        info['device_model'] = 'Unknown'
    
    # GPU memory
    try:
        with open('/boot/config.txt', 'r') as f:
            config = f.read()
            gpu_mem = [line for line in config.split('\n') if line.startswith('gpu_mem')]
            info['gpu_memory'] = gpu_mem[0] if gpu_mem else 'Not set'
    except:
        info['gpu_memory'] = 'Unknown'
    
    # Camera status
    try:
        result = subprocess.run(['vcgencmd', 'get_camera'], 
                              capture_output=True, text=True)
        info['camera_status'] = result.stdout.strip()
    except:
        info['camera_status'] = 'Unknown'
    
    # GPIO status
    info['gpio_available'] = os.path.exists('/sys/class/gpio')
    
    # Model file
    model_path = Path('models/yolov8n_cbam_pothole.pt')
    info['model_exists'] = model_path.exists()
    if model_path.exists():
        info['model_size'] = f"{model_path.stat().st_size / (1024*1024):.1f} MB"
    
    return info

def print_system_info():
    """Print system information"""
    info = get_system_info()
    
    print("=== Pothole Detection System - System Info ===")
    print(f"Platform: {info['platform']}")
    print(f"Device Model: {info['device_model']}")
    print(f"Python Version: {info['python_version'].split()[0]}")
    print(f"Architecture: {info['architecture'][0]}")
    print(f"GPU Memory: {info['gpu_memory']}")
    print(f"Camera Status: {info['camera_status']}")
    print(f"GPIO Available: {info['gpio_available']}")
    print(f"Model File Exists: {info['model_exists']}")
    if info['model_exists']:
        print(f"Model Size: {info['model_size']}")
    print("=" * 50)

if __name__ == "__main__":
    print_system_info()
EOF

chmod +x system_info.py

# Test camera
echo "Testing camera..."
if command -v libcamera-hello &> /dev/null; then
    echo "Camera test (will take a photo in 3 seconds)..."
    timeout 10 libcamera-hello --timeout 3000 --output test_image.jpg 2>/dev/null || true
    if [ -f "test_image.jpg" ]; then
        echo "✓ Camera test successful"
        rm test_image.jpg
    else
        echo "⚠ Camera test failed - check camera connection"
    fi
else
    echo "⚠ libcamera-hello not found - camera test skipped"
fi

# Test GPIO
echo "Testing GPIO..."
python3 -c "
try:
    import RPi.GPIO as GPIO
    print('✓ GPIO module available')
except ImportError:
    print('⚠ GPIO module not available')
"

# Test PyTorch
echo "Testing PyTorch..."
python3 -c "
try:
    import torch
    print(f'✓ PyTorch {torch.__version__} available')
    print(f'  CUDA available: {torch.cuda.is_available()}')
    print(f'  Device count: {torch.cuda.device_count() if torch.cuda.is_available() else 0}')
except ImportError:
    print('⚠ PyTorch not available')
"

# Final instructions
echo
echo "=== Setup Complete ==="
echo
echo "Next steps:"
echo "1. Copy your trained model file to: models/yolov8n_cbam_pothole.pt"
echo "2. Edit configuration: nano config.json"
echo "3. Test the system: python3 system_info.py"
echo "4. Run the system: ./start_pothole_system.sh"
echo "5. Enable auto-start: sudo systemctl start pothole-detector"
echo
echo "Configuration file: config.json"
echo "Logs will be written to: pothole_system.log"
echo "Detection images will be saved to: detections/"
echo
echo "For troubleshooting, check:"
echo "- Camera: libcamera-hello --list-cameras"
echo "- GPIO: python3 -c 'import RPi.GPIO as GPIO; print(\"GPIO OK\")'"
echo "- System: ./system_info.py"
echo
echo "Setup completed successfully!"
echo "Please reboot the system to ensure all changes take effect:"
echo "sudo reboot"
