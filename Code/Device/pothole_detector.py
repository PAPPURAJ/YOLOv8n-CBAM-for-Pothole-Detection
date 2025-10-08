#!/usr/bin/env python3

import cv2
import numpy as np
import torch
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import time

logger = logging.getLogger(__name__)

class PotholeDetector:
    
    def __init__(self, config):
        self.config = config
        self.model = None
        self.camera = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        self.confidence_threshold = config.detection_confidence
        self.iou_threshold = config.detection_iou
        
        logger.info(f"PotholeDetector initialized with device: {self.device}")
    
    def initialize(self):
        try:
            self._load_model()
            self._initialize_camera()
            
            logger.info("PotholeDetector initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize PotholeDetector: {e}")
            raise
    
    def cleanup(self):
        if self.camera:
            self.camera.release()
        logger.info("PotholeDetector cleaned up")
    
    def _load_model(self):
        try:
            model_path = self.config.model_path
            
            if not Path(model_path).exists():
                logger.error(f"Model file not found: {model_path}")
                raise FileNotFoundError(f"Model file not found: {model_path}")
            
            from ultralytics import YOLO
            self.model = YOLO(model_path)
            self.model.to(self.device)
            
            logger.info(f"Pre-trained model loaded from {model_path}")
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    def _initialize_camera(self):
        try:
            for camera_index in [0, 1]:
                self.camera = cv2.VideoCapture(camera_index)
                
                if self.camera.isOpened():
                    self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.camera_width)
                    self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.camera_height)
                    self.camera.set(cv2.CAP_PROP_FPS, self.config.camera_fps)
                    
                    logger.info(f"Camera initialized with index {camera_index}")
                    break
            else:
                raise RuntimeError("Could not initialize camera")
                
        except Exception as e:
            logger.error(f"Failed to initialize camera: {e}")
            raise
    
    def capture_frame(self) -> Optional[np.ndarray]:
        try:
            if not self.camera or not self.camera.isOpened():
                logger.warning("Camera not available")
                return None
            
            ret, frame = self.camera.read()
            if ret:
                return frame
            else:
                logger.warning("Failed to capture frame")
                return None
                
        except Exception as e:
            logger.error(f"Error capturing frame: {e}")
            return None
    
    def detect_potholes(self, frame: np.ndarray) -> List[Dict]:
        try:
            if self.model is None:
                logger.error("Model not loaded")
                return []
            
            results = self.model(frame, 
                               conf=self.confidence_threshold,
                               iou=self.iou_threshold,
                               verbose=False)
            
            detections = []
            
            for result in results:
                if result.boxes is not None:
                    boxes = result.boxes.xyxy.cpu().numpy()
                    confidences = result.boxes.conf.cpu().numpy()
                    classes = result.boxes.cls.cpu().numpy()
                    
                    for box, conf, cls in zip(boxes, confidences, classes):
                        detection = {
                            'bbox': box.tolist(),
                            'confidence': float(conf),
                            'class_id': int(cls),
                            'class_name': 'pothole'
                        }
                        detections.append(detection)
            
            if detections:
                logger.info(f"Detected {len(detections)} pothole(s)")
            
            return detections
            
        except Exception as e:
            logger.error(f"Error in pothole detection: {e}")
            return []
    
    def save_detection_image(self, image_path: str, detections: List[Dict]):
        try:
            frame = self.capture_frame()
            if frame is None:
                logger.warning("No frame to save")
                return
            
            annotated_frame = self._draw_detections(frame, detections)
            
            cv2.imwrite(image_path, annotated_frame)
            logger.info(f"Detection image saved: {image_path}")
            
        except Exception as e:
            logger.error(f"Error saving detection image: {e}")
    
    def _draw_detections(self, frame: np.ndarray, detections: List[Dict]) -> np.ndarray:
        annotated_frame = frame.copy()
        
        for detection in detections:
            bbox = detection['bbox']
            confidence = detection['confidence']
            
            x1, y1, x2, y2 = map(int, bbox)
            
            cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            label = f"Pothole: {confidence:.2f}"
            label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)[0]
            cv2.rectangle(annotated_frame, (x1, y1 - label_size[1] - 10), 
                         (x1 + label_size[0], y1), (0, 255, 0), -1)
            cv2.putText(annotated_frame, label, (x1, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
        
        return annotated_frame
    
    def get_status(self) -> Dict:
        return {
            'model_loaded': self.model is not None,
            'camera_available': self.camera is not None and self.camera.isOpened(),
            'device': str(self.device),
            'confidence_threshold': self.confidence_threshold,
            'iou_threshold': self.iou_threshold
        }