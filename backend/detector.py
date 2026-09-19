"""
PROJECT S.I.G.H.T. Backend — Detector Interface
Pluggable detector backend abstraction. YOLO is replaceable.

Backends:
  - VirtualDetector  (default, uses simulator world targets — no ML inference)
  - YOLODetector     (production — requires ultralytics)
  - PassthroughDetector (for testing — accepts raw dict payloads)
"""

import time
import uuid
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import numpy as np


# ─────────────────────────────────────────────
#  Base Detector Interface
# ─────────────────────────────────────────────

class BaseDetector(ABC):
    """Abstract base class for all S.I.G.H.T. detector backends."""

    @abstractmethod
    def detect(self, frame: np.ndarray, uav_lat: float, uav_lng: float,
               altitude_m: float, timestamp: str) -> List[Dict[str, Any]]:
        """
        Run detection on a frame.
        Returns list of detection dicts matching DetectionRequest schema.
        """
        ...

    @property
    @abstractmethod
    def backend_name(self) -> str:
        ...

    def is_available(self) -> bool:
        return True


# ─────────────────────────────────────────────
#  Virtual Detector (uses world target list)
# ─────────────────────────────────────────────

class VirtualDetector(BaseDetector):
    """
    Detector that reads ground-truth targets from the virtual world.
    No ML inference — designed for integration testing without GPU/YOLO.
    Simulates realistic detection noise (confidence, bbox jitter).
    """

    def __init__(self, confidence_noise_std: float = 5.0, track_counter: int = 0):
        self._conf_noise = confidence_noise_std
        self._track_counter = track_counter
        self._track_map: Dict[str, int] = {}

    @property
    def backend_name(self) -> str:
        return "VIRTUAL_DETECTOR"

    def detect(self, frame: np.ndarray, uav_lat: float, uav_lng: float,
               altitude_m: float, timestamp: str,
               visible_targets: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        Convert world visible targets to detection schema.
        visible_targets: from simulator.world.get_entities_in_camera_fov()
        """
        if not visible_targets:
            return []

        detections = []
        rng = np.random.default_rng(seed=int(time.time() * 1000) % 2**31)

        for target in visible_targets:
            entity_id = target.get("id", str(uuid.uuid4()))

            # Assign stable track ID per entity
            if entity_id not in self._track_map:
                self._track_counter += 1
                self._track_map[entity_id] = self._track_counter
            track_id = self._track_map[entity_id]

            # Base confidence from world + noise
            base_conf = float(target.get("base_confidence", 75.0))
            noisy_conf = float(np.clip(
                rng.normal(base_conf, self._conf_noise), 10.0, 98.0
            ))

            # Simulated normalized bounding box (centre x, y, w, h)
            cx = float(rng.uniform(0.3, 0.7))
            cy = float(rng.uniform(0.3, 0.7))
            w = float(rng.uniform(0.05, 0.25))
            h = float(rng.uniform(0.05, 0.25))

            detections.append({
                "id": f"DET-{entity_id[:6].upper()}-{int(time.time()*1000)%10000}",
                "objectClass": target.get("entity_type", "Unknown"),
                "confidence": round(noisy_conf, 2),
                "normBbox": (cx, cy, w, h),
                "trackId": track_id,
                "persistence": target.get("persistence", 1),
                "lat": float(target.get("lat", uav_lat)),
                "lng": float(target.get("lng", uav_lng)),
                "altitudeM": float(altitude_m),
                "timestamp": timestamp,
                "frameId": 0,
                "source": self.backend_name,
            })

        return detections


# ─────────────────────────────────────────────
#  YOLO Detector (production, optional)
# ─────────────────────────────────────────────

class YOLODetector(BaseDetector):
    """
    Production detector using Ultralytics YOLO.
    Falls back gracefully if ultralytics is not installed.
    Supports any YOLO model (yolo11n.pt, yolov8n.pt, etc.)
    """

    # S.I.G.H.T. relevant class mapping from COCO indices
    COCO_TO_SIGHT = {
        0: "Person",
        2: "Vehicle",
        3: "Vehicle",
        5: "Vehicle",
        7: "Vehicle",
        14: "Animal",
        15: "Animal",
        16: "Animal",
        4: "Aircraft",
        9: "Vessel",
    }

    def __init__(self, model_path: str = "yolo11n.pt"):
        self._model_path = model_path
        self._model = None
        self._available = False
        self._load_model()

    def _load_model(self):
        try:
            from ultralytics import YOLO
            self._model = YOLO(self._model_path)
            self._available = True
        except ImportError:
            self._available = False
        except Exception:
            self._available = False

    def is_available(self) -> bool:
        return self._available

    @property
    def backend_name(self) -> str:
        return f"YOLO({self._model_path})"

    def detect(self, frame: np.ndarray, uav_lat: float, uav_lng: float,
               altitude_m: float, timestamp: str, **kwargs) -> List[Dict[str, Any]]:
        if not self._available or self._model is None:
            return []

        results = self._model(frame, verbose=False)
        detections = []

        for r in results:
            if r.boxes is None:
                continue
            for i, box in enumerate(r.boxes):
                cls_id = int(box.cls[0])
                sight_class = self.COCO_TO_SIGHT.get(cls_id, f"Class_{cls_id}")
                conf = float(box.conf[0]) * 100.0  # Convert to percentage

                # Normalize bbox
                x1, y1, x2, y2 = box.xyxyn[0].tolist()
                cx = (x1 + x2) / 2
                cy = (y1 + y2) / 2
                w = x2 - x1
                h = y2 - y1

                detections.append({
                    "id": f"YOLO-{i}-{int(time.time()*1000)%10000}",
                    "objectClass": sight_class,
                    "confidence": round(conf, 2),
                    "normBbox": (cx, cy, w, h),
                    "trackId": i,
                    "persistence": 1,
                    "lat": uav_lat,
                    "lng": uav_lng,
                    "altitudeM": altitude_m,
                    "timestamp": timestamp,
                    "frameId": 0,
                    "source": self.backend_name,
                })

        return detections


# ─────────────────────────────────────────────
#  Detector Factory
# ─────────────────────────────────────────────

class DetectorFactory:
    """Creates the appropriate detector backend based on configuration."""

    @staticmethod
    def create(backend: str = "virtual", model_path: str = "yolo11n.pt") -> BaseDetector:
        if backend == "yolo":
            detector = YOLODetector(model_path=model_path)
            if detector.is_available():
                return detector
            # Fall back to virtual if YOLO not available
            return VirtualDetector()
        return VirtualDetector()
