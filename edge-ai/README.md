# Edge AI Module

Phase 3B status: the optional YOLO adapter, normalized pixel boxes, lightweight IoU tracking, and per-track persistence are implemented in `backend/detector.py`. The backend remains on `VirtualDetector` by default.

Configuration:

- `SIGHT_DETECTOR_BACKEND=virtual|yolo`
- `SIGHT_YOLO_MODEL_PATH=path/to/model.pt`
- `SIGHT_ALLOW_DETECTOR_FALLBACK=true|false`
- `SIGHT_YOLO_DEVICE=auto|cpu|cuda:0`
- `SIGHT_YOLO_CONFIDENCE=0.25`
- `SIGHT_TRACK_IOU_THRESHOLD=0.3`
- `SIGHT_TRACK_MAX_MISSED_FRAMES=3`

YOLO detections currently report `locationSource=UAV_POSITION` and `targetGeolocationAvailable=false` because camera calibration, pose, and ground-plane ray intersection are not implemented. No target GPS is fabricated.

Future home of the edge perception and tracking stack:
- Sensor capture pipeline (EO / IR thermal camera abstraction)
- YOLO object detection (Person, Vehicle, Vessel, Aircraft, Animal)
- ByteTrack multi-object tracking and persistence counter
- Edge NVMe circular frame buffer for `EVIDENCE` retention

*Note: Frontend receives processed detection metadata; Edge AI operates on the UAV companion computer.*
