#!/usr/bin/env python3

import time
import threading
import logging
from datetime import datetime
from pathlib import Path
import json

from pothole_detector import PotholeDetector
from sensor_manager import SensorManager
from notification_system import NotificationSystem
from backend_client import BackendClient
from config import Config

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pothole_system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PotholeDetectionSystem:
    
    def __init__(self):
        self.config = Config()
        self.running = False
        
        self.detector = PotholeDetector(self.config)
        self.sensors = SensorManager(self.config)
        self.notifications = NotificationSystem(self.config)
        self.backend = BackendClient(self.config)
        
        self.detection_history = []
        self.last_detection_time = 0
        self.min_detection_interval = 5.0
        
        logger.info("Pothole Detection System initialized")
    
    def start(self):
        try:
            logger.info("Starting Pothole Detection System...")
            
            self.detector.initialize()
            self.sensors.initialize()
            self.notifications.initialize()
            
            logger.info("Authenticating with backend server...")
            self.backend.initialize()
            
            self.running = True
            logger.info("System started successfully")
            
            sensor_thread = threading.Thread(target=self._sensor_monitor_loop, daemon=True)
            sensor_thread.start()
            
            self._main_detection_loop()
            
        except Exception as e:
            logger.error(f"Failed to start system: {e}")
            self.stop()
            raise
    
    def stop(self):
        logger.info("Stopping Pothole Detection System...")
        self.running = False
        
        self.detector.cleanup()
        self.sensors.cleanup()
        self.notifications.cleanup()
        self.backend.cleanup()
        
        logger.info("System stopped")
    
    def _sensor_monitor_loop(self):
        while self.running:
            try:
                indicators = self.sensors.check_pothole_indicators()
                
                if indicators['vibration'] or indicators['ultrasonic']:
                    logger.info(f"Sensor indicators detected: {indicators}")
                    
                    self._trigger_detection("sensor_trigger")
                
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in sensor monitor loop: {e}")
                time.sleep(1)
    
    def _main_detection_loop(self):
        frame_count = 0
        detection_interval = self.config.camera_detection_interval
        
        while self.running:
            try:
                frame = self.detector.capture_frame()
                if frame is not None:
                    frame_count += 1
                    
                    if frame_count % detection_interval == 0:
                        self._process_frame(frame)
                
                time.sleep(0.033)
                
            except Exception as e:
                logger.error(f"Error in main detection loop: {e}")
                time.sleep(1)
    
    def _trigger_detection(self, trigger_source):
        try:
            frame = self.detector.capture_frame()
            if frame is not None:
                self._process_frame(frame, trigger_source=trigger_source)
        except Exception as e:
            logger.error(f"Error in triggered detection: {e}")
    
    def _process_frame(self, frame, trigger_source="camera"):
        try:
            detections = self.detector.detect_potholes(frame)
            
            if detections:
                current_time = time.time()
                if current_time - self.last_detection_time >= self.min_detection_interval:
                    
                    sensor_data = self.sensors.get_current_readings()
                    gps_data = self.sensors.get_gps_location()
                    
                    detection_record = {
                        'timestamp': datetime.now().isoformat(),
                        'trigger_source': trigger_source,
                        'detections': detections,
                        'sensor_data': sensor_data,
                        'gps_location': gps_data,
                        'confidence': max([d['confidence'] for d in detections])
                    }
                    
                    self._handle_pothole_detection(detection_record)
                    
                    self.last_detection_time = current_time
                    
        except Exception as e:
            logger.error(f"Error processing frame: {e}")
    
    def _handle_pothole_detection(self, detection_record):
        try:
            logger.info(f"Pothole detected! Confidence: {detection_record['confidence']:.2f}")
            
            self.detection_history.append(detection_record)
            
            self.notifications.notify_pothole_detected(detection_record)
            
            self.backend.upload_detection(detection_record)
            
            self._save_detection_image(detection_record)
            
        except Exception as e:
            logger.error(f"Error handling pothole detection: {e}")
    
    def _save_detection_image(self, detection_record):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            image_path = f"detections/pothole_{timestamp}.jpg"
            
            Path("detections").mkdir(exist_ok=True)
            
            self.detector.save_detection_image(image_path, detection_record['detections'])
            
            detection_record['image_path'] = image_path
            
        except Exception as e:
            logger.error(f"Error saving detection image: {e}")
    
    def get_system_status(self):
        return {
            'running': self.running,
            'detection_count': len(self.detection_history),
            'last_detection': self.detection_history[-1] if self.detection_history else None,
            'sensor_status': self.sensors.get_status(),
            'model_status': self.detector.get_status(),
            'backend_status': self.backend.get_status()
        }

def main():
    system = PotholeDetectionSystem()
    
    try:
        system.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    except Exception as e:
        logger.error(f"System error: {e}")
    finally:
        system.stop()

if __name__ == "__main__":
    main()