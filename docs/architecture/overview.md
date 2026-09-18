# S.I.G.H.T. System Architecture

## Principles
1. **Perception != Communication Decision**: Object detectors (YOLO) identify entities in the camera field of view. The Governor evaluates whether this data serves the current mission objective.
2. **RF Signature Minimization**: Radiating RF energy discloses UAV position and exhausts battery. The system defaults to silence (`SUPPRESS` or `RETAIN`).
3. **Mission Card Driven**: Operators set thresholds and priority zones via structured JSON cards, ensuring adaptable mission parameters without firmware re-flashing.

## Pipeline Sequence
```
Camera Sensor -> YOLO Detection -> ByteTrack -> S.I.G.H.T. Governor -> Packet Controller -> Radio -> Ground Station
```
