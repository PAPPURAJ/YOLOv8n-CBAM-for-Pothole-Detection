#!/usr/bin/env python3

import time
import threading
import logging
import json
from typing import Dict, List, Optional
from datetime import datetime
import subprocess
import os

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    logging.warning("RPi.GPIO not available - display will be simulated")

logger = logging.getLogger(__name__)

class NotificationSystem:
    
    def __init__(self, config):
        self.config = config
        self.initialized = False
        
        self.audio_enabled = config.audio_enabled
        self.audio_device = config.audio_device
        
        self.display_enabled = config.display_enabled
        self.display_pins = config.display_pins
        
        self.notification_duration = config.notification_duration
        self.alert_sound_path = config.alert_sound_path
        
        self.notification_queue = []
        self.notification_lock = threading.Lock()
        self.notification_thread = None
        self.running = False
        
        self.display_state = {
            'system_status': 'initializing',
            'last_detection': None,
            'detection_count': 0,
            'gps_status': 'disconnected'
        }
        
        logger.info("NotificationSystem initialized")
    
    def initialize(self):
        try:
            if self.audio_enabled:
                self._initialize_audio()
            
            if self.display_enabled:
                self._initialize_display()
            
            self.running = True
            self.notification_thread = threading.Thread(target=self._notification_loop, daemon=True)
            self.notification_thread.start()
            
            self.initialized = True
            self.display_state['system_status'] = 'ready'
            
            logger.info("NotificationSystem initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize NotificationSystem: {e}")
            raise
    
    def cleanup(self):
        try:
            self.running = False
            
            if self.notification_thread:
                self.notification_thread.join(timeout=2)
            
            if self.display_enabled and GPIO_AVAILABLE:
                self._turn_off_all_leds()
                GPIO.cleanup()
            
            logger.info("NotificationSystem cleaned up")
            
        except Exception as e:
            logger.error(f"Error during NotificationSystem cleanup: {e}")
    
    def _initialize_audio(self):
        try:
            if self.audio_device:
                os.environ['AUDIODEV'] = self.audio_device
            
            self._test_audio()
            logger.info("Audio system initialized")
            
        except Exception as e:
            logger.warning(f"Audio initialization failed: {e}")
            self.audio_enabled = False
    
    def _initialize_display(self):
        try:
            if GPIO_AVAILABLE:
                GPIO.setmode(GPIO.BCM)
                
                for pin in self.display_pins.values():
                    GPIO.setup(pin, GPIO.OUT)
                    GPIO.output(pin, GPIO.LOW)
                
                self._update_display_status()
                logger.info("Display system initialized")
            else:
                logger.warning("Display running in simulation mode")
                
        except Exception as e:
            logger.error(f"Display initialization failed: {e}")
            self.display_enabled = False
    
    def _test_audio(self):
        try:
            subprocess.run(['speaker-test', '-t', 'sine', '-f', '1000', '-l', '1'], 
                         capture_output=True, timeout=2)
        except Exception as e:
            logger.warning(f"Audio test failed: {e}")
            raise
    
    def _notification_loop(self):
        while self.running:
            try:
                with self.notification_lock:
                    if self.notification_queue:
                        notification = self.notification_queue.pop(0)
                        self._process_notification(notification)
                
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in notification loop: {e}")
                time.sleep(1)
    
    def _process_notification(self, notification: Dict):
        try:
            notification_type = notification.get('type', 'info')
            
            if notification_type == 'pothole_detected':
                self._handle_pothole_notification(notification)
            elif notification_type == 'system_status':
                self._handle_status_notification(notification)
            elif notification_type == 'error':
                self._handle_error_notification(notification)
            
        except Exception as e:
            logger.error(f"Error processing notification: {e}")
    
    def _handle_pothole_notification(self, notification: Dict):
        try:
            detection_data = notification.get('data', {})
            confidence = detection_data.get('confidence', 0.0)
            location = detection_data.get('gps_location', {})
            
            self.display_state['last_detection'] = {
                'timestamp': datetime.now().isoformat(),
                'confidence': confidence,
                'location': location
            }
            self.display_state['detection_count'] += 1
            
            if self.audio_enabled:
                self._play_alert_sound(confidence)
            
            if self.display_enabled:
                self._show_pothole_alert()
            
            logger.info(f"Pothole alert: Confidence={confidence:.2f}, Location={location}")
            
        except Exception as e:
            logger.error(f"Error handling pothole notification: {e}")
    
    def _handle_status_notification(self, notification: Dict):
        try:
            status_data = notification.get('data', {})
            
            self.display_state.update(status_data)
            
            if self.display_enabled:
                self._update_display_status()
            
        except Exception as e:
            logger.error(f"Error handling status notification: {e}")
    
    def _handle_error_notification(self, notification: Dict):
        try:
            error_data = notification.get('data', {})
            error_message = error_data.get('message', 'Unknown error')
            
            if self.display_enabled:
                self._show_error_alert()
            
            if self.audio_enabled:
                self._play_error_sound()
            
            logger.error(f"Error notification: {error_message}")
            
        except Exception as e:
            logger.error(f"Error handling error notification: {e}")
    
    def _play_alert_sound(self, confidence: float):
        try:
            if confidence > 0.8:
                self._play_sound('high_alert')
            elif confidence > 0.5:
                self._play_sound('medium_alert')
            else:
                self._play_sound('low_alert')
                
        except Exception as e:
            logger.error(f"Error playing alert sound: {e}")
    
    def _play_sound(self, sound_type: str):
        try:
            if sound_type == 'high_alert':
                subprocess.Popen(['speaker-test', '-t', 'sine', '-f', '2000', '-l', '1'])
            elif sound_type == 'medium_alert':
                subprocess.Popen(['speaker-test', '-t', 'sine', '-f', '1500', '-l', '1'])
            elif sound_type == 'low_alert':
                subprocess.Popen(['speaker-test', '-t', 'sine', '-f', '1000', '-l', '1'])
            elif sound_type == 'error':
                for _ in range(3):
                    subprocess.run(['speaker-test', '-t', 'sine', '-f', '800', '-l', '1'])
                    time.sleep(0.2)
                    
        except Exception as e:
            logger.error(f"Error playing sound {sound_type}: {e}")
    
    def _play_error_sound(self):
        self._play_sound('error')
    
    def _update_display_status(self):
        try:
            if not self.display_enabled or not GPIO_AVAILABLE:
                return
            
            if self.display_state['system_status'] == 'ready':
                GPIO.output(self.display_pins['system_ready'], GPIO.HIGH)
                GPIO.output(self.display_pins['system_error'], GPIO.LOW)
            elif self.display_state['system_status'] == 'error':
                GPIO.output(self.display_pins['system_ready'], GPIO.LOW)
                GPIO.output(self.display_pins['system_error'], GPIO.HIGH)
            else:
                GPIO.output(self.display_pins['system_ready'], GPIO.LOW)
                GPIO.output(self.display_pins['system_error'], GPIO.LOW)
            
            if self.display_state['gps_status'] == 'connected':
                GPIO.output(self.display_pins['gps_status'], GPIO.HIGH)
            else:
                GPIO.output(self.display_pins['gps_status'], GPIO.LOW)
            
        except Exception as e:
            logger.error(f"Error updating display status: {e}")
    
    def _show_pothole_alert(self):
        try:
            if not self.display_enabled or not GPIO_AVAILABLE:
                return
            
            for _ in range(5):
                GPIO.output(self.display_pins['pothole_detected'], GPIO.HIGH)
                time.sleep(0.2)
                GPIO.output(self.display_pins['pothole_detected'], GPIO.LOW)
                time.sleep(0.2)
            
        except Exception as e:
            logger.error(f"Error showing pothole alert: {e}")
    
    def _show_error_alert(self):
        try:
            if not self.display_enabled or not GPIO_AVAILABLE:
                return
            
            for _ in range(3):
                GPIO.output(self.display_pins['system_error'], GPIO.HIGH)
                time.sleep(0.5)
                GPIO.output(self.display_pins['system_error'], GPIO.LOW)
                time.sleep(0.5)
            
        except Exception as e:
            logger.error(f"Error showing error alert: {e}")
    
    def _turn_off_all_leds(self):
        try:
            if GPIO_AVAILABLE:
                for pin in self.display_pins.values():
                    GPIO.output(pin, GPIO.LOW)
        except Exception as e:
            logger.error(f"Error turning off LEDs: {e}")
    
    def notify_pothole_detected(self, detection_data: Dict):
        notification = {
            'type': 'pothole_detected',
            'data': detection_data,
            'timestamp': time.time()
        }
        
        with self.notification_lock:
            self.notification_queue.append(notification)
    
    def notify_system_status(self, status_data: Dict):
        notification = {
            'type': 'system_status',
            'data': status_data,
            'timestamp': time.time()
        }
        
        with self.notification_lock:
            self.notification_queue.append(notification)
    
    def notify_error(self, error_message: str):
        notification = {
            'type': 'error',
            'data': {'message': error_message},
            'timestamp': time.time()
        }
        
        with self.notification_lock:
            self.notification_queue.append(notification)
    
    def get_status(self) -> Dict:
        return {
            'initialized': self.initialized,
            'audio_enabled': self.audio_enabled,
            'display_enabled': self.display_enabled,
            'running': self.running,
            'queue_size': len(self.notification_queue),
            'display_state': self.display_state
        }