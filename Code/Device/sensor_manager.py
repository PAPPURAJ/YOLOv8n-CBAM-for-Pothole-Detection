#!/usr/bin/env python3

import time
import threading
import logging
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False
    logging.warning("RPi.GPIO not available - running in simulation mode")

try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    logging.warning("pyserial not available - GPS will be simulated")

logger = logging.getLogger(__name__)

@dataclass
class SensorReading:
    timestamp: float
    value: float
    sensor_type: str

@dataclass
class GPSLocation:
    latitude: float
    longitude: float
    altitude: float
    speed: float
    timestamp: float
    fix_quality: int

class SensorManager:
    
    def __init__(self, config):
        self.config = config
        self.initialized = False
        
        self.ultrasonic_trig_pin = config.ultrasonic_trig_pin
        self.ultrasonic_echo_pin = config.ultrasonic_echo_pin
        self.vibration_pin = config.vibration_pin
        self.gps_port = config.gps_port
        self.gps_baudrate = config.gps_baudrate
        
        self.ultrasonic_threshold = config.ultrasonic_threshold
        self.vibration_threshold = config.vibration_threshold
        
        self.readings_history = []
        self.max_history_size = 1000
        self.current_readings = {
            'ultrasonic': None,
            'vibration': None,
            'gps': None
        }
        
        self.gps_serial = None
        
        self.monitoring = False
        self.monitor_thread = None
        
        logger.info("SensorManager initialized")
    
    def initialize(self):
        try:
            if GPIO_AVAILABLE:
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(self.ultrasonic_trig_pin, GPIO.OUT)
                GPIO.setup(self.ultrasonic_echo_pin, GPIO.IN)
                GPIO.setup(self.vibration_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                
                GPIO.add_event_detect(self.vibration_pin, GPIO.FALLING, 
                                    callback=self._vibration_callback, bouncetime=100)
                
                logger.info("GPIO sensors initialized")
            else:
                logger.warning("Running in simulation mode - no GPIO sensors")
            
            self._initialize_gps()
            
            self.monitoring = True
            self.monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
            self.monitor_thread.start()
            
            self.initialized = True
            logger.info("SensorManager initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize SensorManager: {e}")
            raise
    
    def cleanup(self):
        try:
            self.monitoring = False
            
            if self.monitor_thread:
                self.monitor_thread.join(timeout=2)
            
            if self.gps_serial and self.gps_serial.is_open:
                self.gps_serial.close()
            
            if GPIO_AVAILABLE:
                GPIO.cleanup()
            
            logger.info("SensorManager cleaned up")
            
        except Exception as e:
            logger.error(f"Error during SensorManager cleanup: {e}")
    
    def _initialize_gps(self):
        try:
            if SERIAL_AVAILABLE:
                self.gps_serial = serial.Serial(self.gps_port, self.gps_baudrate, timeout=1)
                logger.info(f"GPS initialized on {self.gps_port}")
            else:
                logger.warning("GPS serial not available - using simulation")
                
        except Exception as e:
            logger.warning(f"Failed to initialize GPS: {e} - using simulation")
    
    def _monitoring_loop(self):
        while self.monitoring:
            try:
                ultrasonic_reading = self._read_ultrasonic()
                if ultrasonic_reading:
                    self.current_readings['ultrasonic'] = ultrasonic_reading
                    self._store_reading(ultrasonic_reading)
                
                gps_reading = self._read_gps()
                if gps_reading:
                    self.current_readings['gps'] = gps_reading
                
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                time.sleep(1)
    
    def _vibration_callback(self, channel):
        try:
            timestamp = time.time()
            reading = SensorReading(
                timestamp=timestamp,
                value=1.0,
                sensor_type='vibration'
            )
            
            self.current_readings['vibration'] = reading
            self._store_reading(reading)
            
            logger.debug("Vibration detected")
            
        except Exception as e:
            logger.error(f"Error in vibration callback: {e}")
    
    def _read_ultrasonic(self) -> Optional[SensorReading]:
        try:
            if not GPIO_AVAILABLE:
                import random
                distance = random.uniform(10, 200)
                return SensorReading(
                    timestamp=time.time(),
                    value=distance,
                    sensor_type='ultrasonic'
                )
            
            GPIO.output(self.ultrasonic_trig_pin, GPIO.HIGH)
            time.sleep(0.00001)
            GPIO.output(self.ultrasonic_trig_pin, GPIO.LOW)
            
            start_time = time.time()
            while GPIO.input(self.ultrasonic_echo_pin) == 0:
                if time.time() - start_time > 0.1:
                    return None
                start_time = time.time()
            
            while GPIO.input(self.ultrasonic_echo_pin) == 1:
                if time.time() - start_time > 0.1:
                    return None
                echo_time = time.time()
            
            duration = echo_time - start_time
            distance = (duration * 34300) / 2
            
            return SensorReading(
                timestamp=time.time(),
                value=distance,
                sensor_type='ultrasonic'
            )
            
        except Exception as e:
            logger.error(f"Error reading ultrasonic sensor: {e}")
            return None
    
    def _read_gps(self) -> Optional[GPSLocation]:
        try:
            if not SERIAL_AVAILABLE or not self.gps_serial or not self.gps_serial.is_open:
                import random
                return GPSLocation(
                    latitude=12.9716 + random.uniform(-0.01, 0.01),
                    longitude=77.5946 + random.uniform(-0.01, 0.01),
                    altitude=920.0 + random.uniform(-10, 10),
                    speed=random.uniform(0, 60),
                    timestamp=time.time(),
                    fix_quality=1
                )
            
            if self.gps_serial.in_waiting > 0:
                line = self.gps_serial.readline().decode('utf-8', errors='ignore')
                
                if line.startswith('$GPGGA'):
                    return self._parse_gpgga(line)
            
            return None
            
        except Exception as e:
            logger.error(f"Error reading GPS: {e}")
            return None
    
    def _parse_gpgga(self, line: str) -> Optional[GPSLocation]:
        try:
            parts = line.strip().split(',')
            
            if len(parts) < 15 or parts[6] == '0':
                return None
            
            lat_deg = float(parts[2][:2])
            lat_min = float(parts[2][2:])
            latitude = lat_deg + lat_min / 60.0
            if parts[3] == 'S':
                latitude = -latitude
            
            lon_deg = float(parts[4][:3])
            lon_min = float(parts[4][3:])
            longitude = lon_deg + lon_min / 60.0
            if parts[5] == 'W':
                longitude = -longitude
            
            altitude = float(parts[9]) if parts[9] else 0.0
            fix_quality = int(parts[6])
            
            return GPSLocation(
                latitude=latitude,
                longitude=longitude,
                altitude=altitude,
                speed=0.0,
                timestamp=time.time(),
                fix_quality=fix_quality
            )
            
        except Exception as e:
            logger.error(f"Error parsing GPS data: {e}")
            return None
    
    def _store_reading(self, reading: SensorReading):
        self.readings_history.append(reading)
        
        if len(self.readings_history) > self.max_history_size:
            self.readings_history.pop(0)
    
    def check_pothole_indicators(self) -> Dict[str, bool]:
        indicators = {
            'vibration': False,
            'ultrasonic': False
        }
        
        try:
            if self.current_readings['vibration']:
                vibration_time = self.current_readings['vibration'].timestamp
                if time.time() - vibration_time < 1.0:
                    indicators['vibration'] = True
            
            if self.current_readings['ultrasonic']:
                distance = self.current_readings['ultrasonic'].value
                if distance < self.ultrasonic_threshold:
                    indicators['ultrasonic'] = True
            
        except Exception as e:
            logger.error(f"Error checking pothole indicators: {e}")
        
        return indicators
    
    def get_current_readings(self) -> Dict:
        return {
            'ultrasonic': self.current_readings['ultrasonic'].__dict__ if self.current_readings['ultrasonic'] else None,
            'vibration': self.current_readings['vibration'].__dict__ if self.current_readings['vibration'] else None,
            'gps': self.current_readings['gps'].__dict__ if self.current_readings['gps'] else None
        }
    
    def get_gps_location(self) -> Optional[Dict]:
        if self.current_readings['gps']:
            return self.current_readings['gps'].__dict__
        return None
    
    def get_recent_readings(self, sensor_type: str = None, seconds: int = 60) -> List[Dict]:
        cutoff_time = time.time() - seconds
        recent = []
        
        for reading in self.readings_history:
            if reading.timestamp >= cutoff_time:
                if sensor_type is None or reading.sensor_type == sensor_type:
                    recent.append(reading.__dict__)
        
        return recent
    
    def get_status(self) -> Dict:
        return {
            'initialized': self.initialized,
            'gpio_available': GPIO_AVAILABLE,
            'serial_available': SERIAL_AVAILABLE,
            'gps_connected': self.gps_serial is not None and self.gps_serial.is_open,
            'monitoring': self.monitoring,
            'readings_count': len(self.readings_history),
            'current_readings': {
                'ultrasonic': self.current_readings['ultrasonic'] is not None,
                'vibration': self.current_readings['vibration'] is not None,
                'gps': self.current_readings['gps'] is not None
            }
        }