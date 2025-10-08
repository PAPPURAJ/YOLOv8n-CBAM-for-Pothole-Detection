#!/usr/bin/env python3

import os
import json
from pathlib import Path
from typing import Dict, Any
from dataclasses import dataclass, asdict

@dataclass
class Config:
    
    model_path: str = "models/yolov8n_cbam_pothole.pt"
    detection_confidence: float = 0.25
    detection_iou: float = 0.45
    
    camera_width: int = 640
    camera_height: int = 480
    camera_fps: int = 30
    camera_detection_interval: int = 10
    
    ultrasonic_trig_pin: int = 18
    ultrasonic_echo_pin: int = 24
    ultrasonic_threshold: float = 50.0
    
    vibration_pin: int = 23
    vibration_threshold: float = 0.5
    
    gps_port: str = "/dev/ttyUSB0"
    gps_baudrate: int = 9600
    
    audio_enabled: bool = True
    audio_device: str = "default"
    alert_sound_path: str = "sounds/alert.wav"
    
    display_enabled: bool = True
    display_pins: Dict[str, int] = None
    notification_duration: float = 3.0
    
    backend_url: str = "http://192.168.0.3:8080"
    backend_username: str = "pappuraj.duet@gmail.com"
    backend_password: str = "11223344"
    device_id: str = "pothole_detector_001"
    backend_upload_interval: int = 5
    
    log_level: str = "INFO"
    log_file: str = "pothole_system.log"
    detections_dir: str = "detections"
    
    def __post_init__(self):
        if self.display_pins is None:
            self.display_pins = {
                'system_ready': 25,
                'system_error': 22,
                'gps_status': 27,
                'pothole_detected': 17
            }
    
    @classmethod
    def from_file(cls, config_path: str) -> 'Config':
        try:
            if Path(config_path).exists():
                with open(config_path, 'r') as f:
                    config_data = json.load(f)
                
                if 'display_pins' in config_data:
                    config_data['display_pins'] = config_data['display_pins']
                
                return cls(**config_data)
            else:
                logger.warning(f"Config file not found: {config_path}, using defaults")
                return cls()
                
        except Exception as e:
            print(f"Error loading config file: {e}, using defaults")
            return cls()
    
    def save_to_file(self, config_path: str):
        try:
            config_dict = asdict(self)
            
            Path(config_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_path, 'w') as f:
                json.dump(config_dict, f, indent=2)
            
            print(f"Configuration saved to {config_path}")
            
        except Exception as e:
            print(f"Error saving config file: {e}")
    
    def update_from_env(self):
        env_mappings = {
            'MODEL_PATH': 'model_path',
            'DETECTION_CONFIDENCE': ('detection_confidence', float),
            'DETECTION_IOU': ('detection_iou', float),
            'CAMERA_WIDTH': ('camera_width', int),
            'CAMERA_HEIGHT': ('camera_height', int),
            'CAMERA_FPS': ('camera_fps', int),
            'ULTRASONIC_TRIG_PIN': ('ultrasonic_trig_pin', int),
            'ULTRASONIC_ECHO_PIN': ('ultrasonic_echo_pin', int),
            'ULTRASONIC_THRESHOLD': ('ultrasonic_threshold', float),
            'VIBRATION_PIN': ('vibration_pin', int),
            'VIBRATION_THRESHOLD': ('vibration_threshold', float),
            'GPS_PORT': 'gps_port',
            'GPS_BAUDRATE': ('gps_baudrate', int),
            'AUDIO_ENABLED': ('audio_enabled', lambda x: x.lower() == 'true'),
            'AUDIO_DEVICE': 'audio_device',
            'DISPLAY_ENABLED': ('display_enabled', lambda x: x.lower() == 'true'),
            'BACKEND_URL': 'backend_url',
            'BACKEND_USERNAME': 'backend_username',
            'BACKEND_PASSWORD': 'backend_password',
            'DEVICE_ID': 'device_id',
            'LOG_LEVEL': 'log_level'
        }
        
        for env_var, config_attr in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value is not None:
                if isinstance(config_attr, tuple):
                    attr_name, type_func = config_attr
                    setattr(self, attr_name, type_func(env_value))
                else:
                    setattr(self, config_attr, env_value)
    
    def validate(self) -> Dict[str, Any]:
        issues = []
        warnings = []
        
        if not Path(self.model_path).exists():
            issues.append(f"Model file not found: {self.model_path}")
        
        if self.camera_width < 320 or self.camera_height < 240:
            warnings.append("Camera resolution is quite low")
        
        if self.camera_width > 1920 or self.camera_height > 1080:
            warnings.append("Camera resolution is very high - may impact performance")
        
        valid_pins = list(range(2, 28))
        for pin_name, pin_num in self.display_pins.items():
            if pin_num not in valid_pins:
                issues.append(f"Invalid GPIO pin for {pin_name}: {pin_num}")
        
        if self.ultrasonic_trig_pin not in valid_pins:
            issues.append(f"Invalid ultrasonic trigger pin: {self.ultrasonic_trig_pin}")
        
        if self.ultrasonic_echo_pin not in valid_pins:
            issues.append(f"Invalid ultrasonic echo pin: {self.ultrasonic_echo_pin}")
        
        if self.vibration_pin not in valid_pins:
            issues.append(f"Invalid vibration pin: {self.vibration_pin}")
        
        if not 0.0 <= self.detection_confidence <= 1.0:
            issues.append(f"Detection confidence must be between 0.0 and 1.0: {self.detection_confidence}")
        
        if not 0.0 <= self.detection_iou <= 1.0:
            issues.append(f"Detection IoU must be between 0.0 and 1.0: {self.detection_iou}")
        
        if not self.backend_url:
            warnings.append("Backend URL not configured")
        
        if not self.backend_username:
            warnings.append("Backend username not configured")
        
        if not self.backend_password:
            warnings.append("Backend password not configured")
        
        if not self.device_id:
            issues.append("Device ID not configured")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings
        }
    
    def get_summary(self) -> str:
        summary = []
        summary.append("=== Pothole Detection System Configuration ===")
        summary.append(f"Model: {self.model_path}")
        summary.append(f"Detection: conf={self.detection_confidence}, iou={self.detection_iou}")
        summary.append(f"Camera: {self.camera_width}x{self.camera_height} @ {self.camera_fps}fps")
        summary.append(f"Sensors: ultrasonic({self.ultrasonic_trig_pin},{self.ultrasonic_echo_pin}), vibration({self.vibration_pin}), GPS({self.gps_port})")
        summary.append(f"Notifications: audio={self.audio_enabled}, display={self.display_enabled}")
        summary.append(f"Backend: {self.backend_url}")
        summary.append(f"Device ID: {self.device_id}")
        summary.append("=" * 50)
        
        return "\n".join(summary)

default_config = Config()

def load_config(config_path: str = "config.json") -> Config:
    config = Config.from_file(config_path)
    config.update_from_env()
    
    validation = config.validate()
    if not validation['valid']:
        print("Configuration issues found:")
        for issue in validation['issues']:
            print(f"  ERROR: {issue}")
    
    if validation['warnings']:
        print("Configuration warnings:")
        for warning in validation['warnings']:
            print(f"  WARNING: {warning}")
    
    return config

if __name__ == "__main__":
    config = Config()
    config.save_to_file("config.json")
    print(config.get_summary())
    
    loaded_config = load_config("config.json")
    print("\nLoaded configuration:")
    print(loaded_config.get_summary())