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
from dataclasses import dataclass
from pathlib import Path
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


class DetectionNormalizer:
    """Convert detector boxes and classes into the S.I.G.H.T. contract."""

    COCO_TO_SIGHT = {
        0: "Person",
        1: "Vehicle",
        2: "Vehicle",
        3: "Vehicle",
        4: "Aircraft",
        5: "Vehicle",
        7: "Vehicle",
        8: "Vessel",
        14: "Animal",
        15: "Animal",
        16: "Animal",
        17: "Animal",
        18: "Animal",
        19: "Animal",
        20: "Animal",
        21: "Animal",
        22: "Animal",
        23: "Animal",
    }

    @classmethod
    def normalize_bbox(cls, xyxy: Any) -> Optional[tuple[float, float, float, float]]:
        values = [float(value) for value in xyxy]
        if len(values) != 4 or not all(np.isfinite(value) for value in values):
            return None
        x1, y1, x2, y2 = values
        x1, x2 = sorted((max(0.0, min(1.0, x1)), max(0.0, min(1.0, x2))))
        y1, y2 = sorted((max(0.0, min(1.0, y1)), max(0.0, min(1.0, y2))))
        if x2 <= x1 or y2 <= y1:
            return None
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0, x2 - x1, y2 - y1)

    @classmethod
    def sight_class(cls, class_id: int) -> Optional[str]:
        return cls.COCO_TO_SIGHT.get(int(class_id))


def _bbox_iou(first: tuple[float, float, float, float], second: tuple[float, float, float, float]) -> float:
    def corners(box):
        cx, cy, width, height = box
        return cx - width / 2, cy - height / 2, cx + width / 2, cy + height / 2

    ax1, ay1, ax2, ay2 = corners(first)
    bx1, by1, bx2, by2 = corners(second)
    intersection = max(0.0, min(ax2, bx2) - max(ax1, bx1)) * max(0.0, min(ay2, by2) - max(ay1, by1))
    first_area = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    second_area = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = first_area + second_area - intersection
    return intersection / union if union else 0.0


@dataclass
class TrackState:
    track_id: int
    object_class: str
    bbox: tuple[float, float, float, float]
    first_seen_frame: int
    last_seen_frame: int
    last_seen_timestamp: str
    age: int = 1
    missed_frames: int = 0


class StableTracker:
    """Small deterministic IoU tracker for the optional YOLO branch."""

    def __init__(self, iou_threshold: float = 0.3, max_missed_frames: int = 3):
        self.iou_threshold = iou_threshold
        self.max_missed_frames = max_missed_frames
        self._next_track_id = 1
        self._tracks: Dict[int, TrackState] = {}
        self.expired_count = 0

    @property
    def active_tracks(self) -> List[TrackState]:
        return list(self._tracks.values())

    def update(self, detections: List[Dict[str, Any]], frame_id: int, timestamp: str) -> List[Dict[str, Any]]:
        unmatched_tracks = set(self._tracks)
        matched_detections: List[Dict[str, Any]] = []

        for detection in detections:
            bbox = detection["normBbox"]
            candidates = [
                track for track_id, track in self._tracks.items()
                if track_id in unmatched_tracks and track.object_class == detection["objectClass"]
            ]
            match = max(candidates, key=lambda track: _bbox_iou(track.bbox, bbox), default=None)
            if match is not None and _bbox_iou(match.bbox, bbox) >= self.iou_threshold:
                match.bbox = bbox
                match.last_seen_frame = frame_id
                match.last_seen_timestamp = timestamp
                match.age += 1
                match.missed_frames = 0
                unmatched_tracks.remove(match.track_id)
                detection["trackId"] = match.track_id
                detection["persistence"] = match.age
            else:
                track = TrackState(
                    track_id=self._next_track_id,
                    object_class=detection["objectClass"],
                    bbox=bbox,
                    first_seen_frame=frame_id,
                    last_seen_frame=frame_id,
                    last_seen_timestamp=timestamp,
                )
                self._tracks[track.track_id] = track
                self._next_track_id += 1
                detection["trackId"] = track.track_id
                detection["persistence"] = 1
            matched_detections.append(detection)

        for track_id in list(unmatched_tracks):
            track = self._tracks[track_id]
            track.missed_frames += 1
            if track.missed_frames > self.max_missed_frames:
                del self._tracks[track_id]
                self.expired_count += 1

        return matched_detections


class PersistenceManager:
    """Tracks consecutive observations independently of detector confidence."""

    def __init__(self):
        self._counts: Dict[int, int] = {}

    def update(self, track_id: int) -> int:
        self._counts[track_id] = self._counts.get(track_id, 0) + 1
        return self._counts[track_id]

    def expire(self, active_track_ids: set[int]) -> None:
        for track_id in set(self._counts) - active_track_ids:
            del self._counts[track_id]


def normalize_world_target(target: Dict[str, Any]) -> Dict[str, Any]:
    """Adapt the synthetic-world target shape to the detector input contract."""
    normalized = dict(target)
    normalized["id"] = target.get("id", target.get("entity_id"))
    normalized["entity_type"] = target.get("entity_type", target.get("class", "Unknown"))
    normalized["persistence"] = target.get("persistence", 1)
    return normalized


def normalize_world_targets(targets: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Normalize all visible synthetic-world targets without inventing persistence."""
    return [normalize_world_target(target) for target in (targets or [])]


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
        self._detection_counter = 0
        self._track_map: Dict[str, int] = {}

    @property
    def backend_name(self) -> str:
        return "VIRTUAL_DETECTOR"

    def detect(self, frame: np.ndarray, uav_lat: float, uav_lng: float,
               altitude_m: float, timestamp: str,
               visible_targets: Optional[List[Dict[str, Any]]] = None,
               frame_id: int = 0) -> List[Dict[str, Any]]:
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
            self._detection_counter += 1

            # Base confidence from world + noise
            base_conf = float(target.get("base_confidence", 75.0))
            noisy_conf = float(np.clip(
                rng.normal(base_conf, self._conf_noise), 10.0, 98.0
            ))

            # Preserve the synthetic world's projected box when available.
            world_bbox = target.get("norm_bbox")
            if isinstance(world_bbox, (tuple, list)) and len(world_bbox) == 4:
                cx, cy, w, h = (float(value) for value in world_bbox)
            else:
                cx = float(rng.uniform(0.3, 0.7))
                cy = float(rng.uniform(0.3, 0.7))
                w = float(rng.uniform(0.05, 0.25))
                h = float(rng.uniform(0.05, 0.25))

            detections.append({
                "id": f"DET-{entity_id[:6].upper()}-{self._detection_counter:06d}",
                "objectClass": target.get("entity_type", "Unknown"),
                "confidence": round(noisy_conf, 2),
                "normBbox": (cx, cy, w, h),
                "trackId": track_id,
                "persistence": target.get("persistence", 1),
                "lat": float(target.get("lat", uav_lat)),
                "lng": float(target.get("lng", uav_lng)),
                "altitudeM": float(altitude_m),
                "timestamp": timestamp,
                "frameId": frame_id,
                "source": self.backend_name,
                "locationSource": "SYNTHETIC_WORLD",
                "targetGeolocationAvailable": True,
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

    def __init__(self, model_path: str = "yolo11n.pt", device: str = "auto",
                 confidence_threshold: float = 0.25, iou_threshold: float = 0.3,
                 max_missed_frames: int = 3):
        self._model_path = model_path
        self.device = device
        self.confidence_threshold = confidence_threshold
        self._model = None
        self._available = False
        self.load_error: Optional[str] = None
        self.last_inference_ms: Optional[float] = None
        self.inference_count = 0
        self.last_successful_inference: Optional[str] = None
        self.tracker = StableTracker(iou_threshold=iou_threshold, max_missed_frames=max_missed_frames)
        self.persistence = PersistenceManager()
        self._detection_counter = 0
        self._load_model()

    def _load_model(self):
        if not Path(self._model_path).is_file():
            self.load_error = f"Model file not found: {self._model_path}"
            return
        try:
            from ultralytics import YOLO
            self._model = YOLO(self._model_path)
            self._available = True
        except ImportError:
            self.load_error = "ultralytics is not installed"
            self._available = False
        except Exception as exc:
            self.load_error = str(exc)
            self._available = False

    def is_available(self) -> bool:
        return self._available

    @property
    def backend_name(self) -> str:
        return f"YOLO({self._model_path})"

    def detect(self, frame: np.ndarray, uav_lat: float, uav_lng: float,
               altitude_m: float, timestamp: str, frame_id: int = 0, **kwargs) -> List[Dict[str, Any]]:
        if not self._available or self._model is None:
            return []

        inference_started = time.perf_counter()
        results = self._model(frame, verbose=False, conf=self.confidence_threshold)
        self.last_inference_ms = round((time.perf_counter() - inference_started) * 1000.0, 3)
        self.inference_count += 1
        self.last_successful_inference = timestamp
        detections = []

        for result in results:
            r = result
            if r.boxes is None:
                continue
            for box in r.boxes:
                cls_id = int(box.cls[0])
                sight_class = DetectionNormalizer.sight_class(cls_id)
                if sight_class is None:
                    continue
                conf = float(box.conf[0]) * 100.0  # Convert to percentage

                norm_bbox = DetectionNormalizer.normalize_bbox(box.xyxyn[0].tolist())
                if norm_bbox is None:
                    continue
                self._detection_counter += 1

                detections.append({
                    "id": f"YOLO-{self._detection_counter:08d}",
                    "objectClass": sight_class,
                    "confidence": round(conf, 2),
                    "normBbox": norm_bbox,
                    "trackId": 0,
                    "persistence": 1,
                    "lat": uav_lat,
                    "lng": uav_lng,
                    "altitudeM": altitude_m,
                    "timestamp": timestamp,
                    "frameId": frame_id,
                    "source": self.backend_name,
                    "locationSource": "UAV_POSITION",
                    "targetGeolocationAvailable": False,
                })

        tracked = self.tracker.update(detections, frame_id=frame_id, timestamp=timestamp)
        self.persistence.expire({track.track_id for track in self.tracker.active_tracks})
        for detection in tracked:
            detection["persistence"] = self.persistence.update(detection["trackId"])
        return detections


# ─────────────────────────────────────────────
#  Detector Factory
# ─────────────────────────────────────────────

class DetectorFactory:
    """Creates the appropriate detector backend based on configuration."""

    @staticmethod
    def create(backend: str = "virtual", model_path: str = "yolo11n.pt", **kwargs) -> BaseDetector:
        if backend == "yolo":
            detector = YOLODetector(model_path=model_path, **kwargs)
            if detector.is_available():
                return detector
            # Fall back to virtual if YOLO not available
            return VirtualDetector()
        return VirtualDetector()
