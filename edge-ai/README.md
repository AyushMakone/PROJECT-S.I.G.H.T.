# Edge AI Module

Future home of the edge perception and tracking stack:
- Sensor capture pipeline (EO / IR thermal camera abstraction)
- YOLO object detection (Person, Vehicle, Vessel, Aircraft, Animal)
- ByteTrack multi-object tracking and persistence counter
- Edge NVMe circular frame buffer for `EVIDENCE` retention

*Note: Frontend receives processed detection metadata; Edge AI operates on the UAV companion computer.*
