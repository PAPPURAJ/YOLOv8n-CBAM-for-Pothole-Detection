#!/usr/bin/env python3

from dataclasses import dataclass, field
from typing import Dict
from pathlib import Path

@dataclass
class Config:
    """
    Centralized Configuration Management.
    Stores tunable parameters for Model, Hardware, and Network subsystems.
    """
    
    # --- Computer Vision ---
    model_path: str = "models/yolov8n_cbam.pt"
    confidence_threshold: float = 0.25
    
    # --- Hardware Mapping ---
    camera_id: int = 0
    # Ultrasonic Pins (Trig, Echo)
    sensor_pins: Dict[str, int] = field(default_factory=lambda: {'trig': 18, 'echo': 24})
    
    # --- Backend Integration ---
    api_endpoint: str = "https://api.pothole-monitor.com/v1"
    device_token: str = "dev_12345"

    @classmethod
    def load(cls, path: str = "config.json") -> 'Config':
        """
        Hydrates configuration from a persistent JSON file.
        """
        # Check if file exists
        # Read JSON
        # Validate critical fields
        return cls()

    def save(self):
        """
        Persists current runtime configuration to disk.
        """
        # Serialize to JSON
        ...