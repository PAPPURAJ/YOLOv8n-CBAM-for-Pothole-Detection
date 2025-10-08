#!/usr/bin/env python3

import time
import threading
import logging
import json
import requests
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
import queue
import hashlib

logger = logging.getLogger(__name__)

class BackendClient:
    
    def __init__(self, config):
        self.config = config
        self.initialized = False
        
        self.server_url = config.backend_url
        self.username = config.backend_username
        self.password = config.backend_password
        self.device_id = config.device_id
        self.upload_interval = config.backend_upload_interval
        
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = 0
        
        self.upload_queue = queue.Queue()
        self.upload_thread = None
        self.running = False
        
        self.upload_stats = {
            'total_uploads': 0,
            'successful_uploads': 0,
            'failed_uploads': 0,
            'last_upload': None,
            'last_error': None
        }
        
        self.offline_storage_path = Path("offline_detections")
        self.offline_storage_path.mkdir(exist_ok=True)
        
        self.token_storage_path = Path("tokens.json")
        
        logger.info("BackendClient initialized")
    
    def initialize(self):
        try:
            self._load_saved_tokens()
            
            if self._authenticate():
                logger.info("Initial authentication successful")
                self._save_tokens()
            else:
                logger.warning("Initial authentication failed - will store offline")
            
            if self._test_connection():
                logger.info("Backend connection test successful")
            else:
                logger.warning("Backend connection test failed - will store offline")
            
            self.running = True
            self.upload_thread = threading.Thread(target=self._upload_loop, daemon=True)
            self.upload_thread.start()
            
            self._process_offline_detections()
            
            self.initialized = True
            logger.info("BackendClient initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize BackendClient: {e}")
            raise
    
    def cleanup(self):
        try:
            self.running = False
            
            if self.upload_thread:
                self.upload_thread.join(timeout=5)
            
            logger.info("BackendClient cleaned up")
            
        except Exception as e:
            logger.error(f"Error during BackendClient cleanup: {e}")
    
    def _load_saved_tokens(self):
        try:
            if self.token_storage_path.exists():
                with open(self.token_storage_path, 'r') as f:
                    token_data = json.load(f)
                
                self.access_token = token_data.get('access_token')
                self.refresh_token = token_data.get('refresh_token')
                self.token_expires_at = token_data.get('expires_at', 0)
                
                if self.access_token and time.time() < (self.token_expires_at - 300):
                    logger.info("Loaded valid saved tokens")
                else:
                    logger.info("Saved tokens expired, will re-authenticate")
                    self.access_token = None
                    self.refresh_token = None
                    self.token_expires_at = 0
            else:
                logger.info("No saved tokens found")
                
        except Exception as e:
            logger.warning(f"Error loading saved tokens: {e}")
            self.access_token = None
            self.refresh_token = None
            self.token_expires_at = 0
    
    def _save_tokens(self):
        try:
            if self.access_token and self.refresh_token:
                token_data = {
                    'access_token': self.access_token,
                    'refresh_token': self.refresh_token,
                    'expires_at': self.token_expires_at,
                    'saved_at': time.time()
                }
                
                with open(self.token_storage_path, 'w') as f:
                    json.dump(token_data, f, indent=2)
                
                logger.info("Tokens saved successfully")
                
        except Exception as e:
            logger.error(f"Error saving tokens: {e}")
    
    def _authenticate(self) -> bool:
        try:
            auth_data = {
                'username': self.username,
                'password': self.password
            }
            
            response = requests.post(
                f"{self.server_url}/api/auth/login",
                json=auth_data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('accessToken')
                self.refresh_token = token_data.get('refreshToken')
                
                expires_in = token_data.get('expiresIn', 900)
                self.token_expires_at = time.time() + expires_in - 60
                
                logger.info("Authentication successful")
                return True
            else:
                logger.error(f"Authentication failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    def _refresh_access_token(self) -> bool:
        try:
            if not self.refresh_token:
                return self._authenticate()
            
            refresh_data = {
                'refreshToken': self.refresh_token
            }
            
            response = requests.post(
                f"{self.server_url}/api/auth/refresh",
                json=refresh_data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('accessToken')
                
                expires_in = token_data.get('expiresIn', 900)
                self.token_expires_at = time.time() + expires_in - 60
                
                logger.info("Token refreshed successfully")
                self._save_tokens()
                return True
            else:
                logger.warning("Token refresh failed, re-authenticating")
                return self._authenticate()
                
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return self._authenticate()
    
    def _get_auth_headers(self) -> Dict[str, str]:
        if time.time() >= self.token_expires_at:
            if not self._refresh_access_token():
                logger.error("Failed to refresh token")
                return {}
        
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json',
            'User-Agent': f'PotholeDetector/{self.device_id}'
        }
    
    def _test_connection(self) -> bool:
        try:
            if not self._authenticate():
                return False
            
            headers = self._get_auth_headers()
            if not headers:
                return False
            
            response = requests.get(
                f"{self.server_url}/api/health",
                headers=headers,
                timeout=10
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.warning(f"Backend connection test failed: {e}")
            return False
    
    def _upload_loop(self):
        while self.running:
            try:
                try:
                    detection_data = self.upload_queue.get(timeout=1.0)
                    self._upload_detection(detection_data)
                    self.upload_queue.task_done()
                except queue.Empty:
                    continue
                
            except Exception as e:
                logger.error(f"Error in upload loop: {e}")
                time.sleep(5)
    
    def _upload_detection(self, detection_data: Dict):
        try:
            upload_data = self._prepare_upload_data(detection_data)
            
            if self._send_to_backend(upload_data):
                self.upload_stats['successful_uploads'] += 1
                self.upload_stats['last_upload'] = datetime.now().isoformat()
                logger.info("Detection uploaded successfully")
            else:
                self._store_offline(detection_data)
                self.upload_stats['failed_uploads'] += 1
                self.upload_stats['last_error'] = "Upload failed"
                logger.warning("Upload failed - stored offline")
            
            self.upload_stats['total_uploads'] += 1
            
        except Exception as e:
            logger.error(f"Error uploading detection: {e}")
            self._store_offline(detection_data)
            self.upload_stats['failed_uploads'] += 1
            self.upload_stats['last_error'] = str(e)
    
    def _prepare_upload_data(self, detection_data: Dict) -> Dict:
        try:
            gps_location = detection_data.get('gps_location', {})
            sensor_data = detection_data.get('sensor_data', {})
            detections = detection_data.get('detections', [])
            
            upload_data = {
                'device_id': self.device_id,
                'timestamp': detection_data.get('timestamp'),
                'trigger_source': detection_data.get('trigger_source'),
                'location': {
                    'latitude': gps_location.get('latitude'),
                    'longitude': gps_location.get('longitude'),
                    'altitude': gps_location.get('altitude'),
                    'speed': gps_location.get('speed'),
                    'fix_quality': gps_location.get('fix_quality')
                },
                'detections': detections,
                'sensor_data': {
                    'ultrasonic_distance': sensor_data.get('ultrasonic', {}).get('value'),
                    'vibration_detected': sensor_data.get('vibration') is not None,
                    'confidence': detection_data.get('confidence')
                },
                'image_path': detection_data.get('image_path'),
                'metadata': {
                    'detection_count': len(detections),
                    'max_confidence': max([d.get('confidence', 0) for d in detections]) if detections else 0
                }
            }
            
            return upload_data
            
        except Exception as e:
            logger.error(f"Error preparing upload data: {e}")
            raise
    
    def _send_to_backend(self, upload_data: Dict) -> bool:
        try:
            headers = self._get_auth_headers()
            if not headers:
                logger.error("No valid authentication headers")
                return False
            
            response = requests.post(
                f"{self.server_url}/api/detections",
                json=upload_data,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 201:
                logger.info("Detection uploaded to backend successfully")
                return True
            elif response.status_code == 401:
                logger.error("Authentication failed - token expired or invalid")
                if self._authenticate():
                    headers = self._get_auth_headers()
                    if headers:
                        retry_response = requests.post(
                            f"{self.server_url}/api/detections",
                            json=upload_data,
                            headers=headers,
                            timeout=30
                        )
                        if retry_response.status_code == 201:
                            logger.info("Detection uploaded after re-authentication")
                            return True
                return False
            elif response.status_code == 403:
                logger.error("Access forbidden - check user permissions")
                return False
            elif response.status_code == 429:
                logger.warning("Rate limited - will retry later")
                return False
            else:
                logger.warning(f"Upload failed with status {response.status_code}: {response.text}")
                return False
                
        except requests.exceptions.Timeout:
            logger.warning("Upload timeout - storing offline")
            return False
        except requests.exceptions.ConnectionError:
            logger.warning("Connection error - storing offline")
            return False
        except Exception as e:
            logger.error(f"Error sending to backend: {e}")
            return False
    
    def _store_offline(self, detection_data: Dict):
        try:
            timestamp = detection_data.get('timestamp', datetime.now().isoformat())
            filename = f"detection_{timestamp.replace(':', '-').replace('.', '-')}.json"
            filepath = self.offline_storage_path / filename
            
            with open(filepath, 'w') as f:
                json.dump(detection_data, f, indent=2)
            
            logger.info(f"Detection stored offline: {filename}")
            
        except Exception as e:
            logger.error(f"Error storing offline: {e}")
    
    def _process_offline_detections(self):
        try:
            offline_files = list(self.offline_storage_path.glob("detection_*.json"))
            logger.info(f"Found {len(offline_files)} offline detections to process")
            
            for filepath in offline_files:
                try:
                    with open(filepath, 'r') as f:
                        detection_data = json.load(f)
                    
                    self.upload_queue.put(detection_data)
                    
                    filepath.unlink()
                    
                except Exception as e:
                    logger.error(f"Error processing offline file {filepath}: {e}")
                    
        except Exception as e:
            logger.error(f"Error processing offline detections: {e}")
    
    def upload_detection(self, detection_data: Dict):
        try:
            self.upload_queue.put(detection_data)
            logger.info("Detection added to upload queue")
            
        except Exception as e:
            logger.error(f"Error adding detection to queue: {e}")
            self._store_offline(detection_data)
    
    def upload_image(self, image_path: str, detection_id: str) -> bool:
        try:
            if not Path(image_path).exists():
                logger.error(f"Image file not found: {image_path}")
                return False
            
            headers = self._get_auth_headers()
            if not headers:
                logger.error("No valid authentication headers")
                return False
            
            if 'Content-Type' in headers:
                del headers['Content-Type']
            
            with open(image_path, 'rb') as f:
                files = {'image': f}
                data = {'detection_id': detection_id}
                
                response = requests.post(
                    f"{self.server_url}/api/detections/{detection_id}/image",
                    files=files,
                    data=data,
                    headers=headers,
                    timeout=60
                )
            
            if response.status_code == 200:
                logger.info(f"Image uploaded successfully for detection {detection_id}")
                return True
            elif response.status_code == 401:
                logger.error("Authentication failed for image upload")
                return False
            else:
                logger.warning(f"Image upload failed with status {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error uploading image: {e}")
            return False
    
    def get_upload_stats(self) -> Dict:
        return {
            'total_uploads': self.upload_stats['total_uploads'],
            'successful_uploads': self.upload_stats['successful_uploads'],
            'failed_uploads': self.upload_stats['failed_uploads'],
            'success_rate': (
                self.upload_stats['successful_uploads'] / max(1, self.upload_stats['total_uploads'])
            ) * 100,
            'last_upload': self.upload_stats['last_upload'],
            'last_error': self.upload_stats['last_error'],
            'queue_size': self.upload_queue.qsize(),
            'offline_files': len(list(self.offline_storage_path.glob("detection_*.json")))
        }
    
    def get_status(self) -> Dict:
        return {
            'initialized': self.initialized,
            'server_url': self.server_url,
            'device_id': self.device_id,
            'running': self.running,
            'queue_size': self.upload_queue.qsize(),
            'upload_stats': self.get_upload_stats()
        }