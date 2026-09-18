# PROJECT S.I.G.H.T. — Simulator Architecture & Verification (Phase 2)

## 1. Overview
The **Virtual UAV Simulator** (`simulator/`) provides a self-contained, independent simulation environment that models:
- **PX4 SITL Autopilot Dynamics**: 6-DOF kinematics, flight state transitions (`DISARMED`, `ARMING`, `ARMED`, `TAKEOFF`, `AUTO_MISSION`, `LOITER`, `RTH`, `LANDING`, `LANDED`), waypoint acceptance, climb/descent, and dynamic battery discharge.
- **MAVLink 2.0 Broadcast Server**: Genuine UDP socket broadcast on `127.0.0.1:14550` (or companion computer port `14540`), sending `HEARTBEAT`, `GLOBAL_POSITION_INT`, `ATTITUDE`, and `SYS_STATUS` packets.
- **Gazebo Synthetic World**: Coordinates and spatial bounds of the perimeter testing ground (Sector Alpha & Beta, perimeter roads, terrain elevation) with ground targets (`Person`, `Vehicle`, `Animal`).
- **Simulated UAV Camera**: OpenCV-based optical sensor generating real RGB frames at configurable resolution (default 640x480, up to 1280x720) and frame rate (10–30 FPS), complete with timestamp overlay, telemetry HUD, and projection of physical target entities when within the camera's FOV.

---

## 2. Directory Structure
```
simulator/
├── px4/
│   ├── autopilot_state.py      # 6-DOF kinematics and flight state machine
│   ├── mavlink_server.py       # MAVLink 2.0 UDP broadcast engine
│   └── __init__.py
├── gazebo/
│   ├── world_server.py         # Proving ground 3D world with physical targets
│   ├── camera_sensor.py        # OpenCV synthetic camera frame generator
│   └── __init__.py
├── missions/
│   └── perimeter_mission.json  # Predefined tactical flight plan
├── scripts/
│   ├── start_simulation.py     # Background simulator CLI
│   ├── stop_simulation.py      # Clean simulator shutdown
│   ├── run_mission.py          # Autonomous waypoint flight plan runner
│   ├── reset_simulation.py     # Simulator state reset
│   ├── start_simulation.bat
│   ├── stop_simulation.bat
│   ├── run_mission.bat
│   └── reset_simulation.bat
├── tests/
│   ├── test_flight_lifecycle.py # Arm -> Takeoff -> Waypoint Nav -> Land -> Disarm
│   ├── test_mavlink_stream.py   # MAVLink UDP packet transmission and decoding
│   └── test_camera_stream.py    # Camera frame format, resolution, and targets
├── simulator_interface.py       # Programmatic Python API
├── telemetry_adapter.py         # Schema converter for GCS and S.I.G.H.T. Core
└── README.md
```

---

## 3. Interfaces & MAVLink Specifications
### MAVLink UDP Stream
- **Target Host**: `127.0.0.1`
- **Default Port**: `14550` (configurable)
- **Protocol**: MAVLink 2.0 (`pymavlink`)
- **Messages**:
  - `HEARTBEAT` (Type: `MAV_TYPE_QUADROTOR`, Autopilot: `MAV_AUTOPILOT_PX4`, 1 Hz)
  - `GLOBAL_POSITION_INT` (Lat, Lng * 1e7, Alt in mm, 10 Hz)
  - `ATTITUDE` (Roll, Pitch, Yaw in radians, 10 Hz)
  - `SYS_STATUS` (Battery percentage, voltage in mV, 2 Hz)

### Camera Sensor Specifications
- **Sensor Type**: Downward-facing Gimbal EO/IR Camera
- **Horizontal FOV**: 75.0°
- **Vertical FOV**: 55.0°
- **Default Resolution**: 640 × 480 pixels
- **Configurable Resolutions**: Supported up to 1280 × 720 (HD)
- **Framerate**: 15 FPS default (configurable 10–30 FPS)
- **Encoding**: Raw BGR `numpy.ndarray` & JPEG bytes (`get_latest_frame_jpeg()`)

---

## 4. Execution & Verification Commands

### Run Automated Tests
```bash
python -m pytest simulator/tests/ -v
```
*Result*: 7/7 tests passed in 0.75s.

### Run Waypoint Mission
```bash
python simulator/scripts/run_mission.py --save-frames
```

### Reset Simulation
```bash
python simulator/scripts/reset_simulation.py
```

### Start Background Simulation
```bash
python simulator/scripts/start_simulation.py --port 14550
```

---

## 5. Phase 2 Completion Checklist
- [x] Controllable virtual UAV flight dynamics (`autopilot_state.py`)
- [x] Waypoint navigation along predefined flight plan
- [x] Arming, takeoff, and landing state transitions
- [x] Real MAVLink 2.0 UDP broadcast engine verified with receiver decoding
- [x] Real camera frame generation producing optical images with targets and timestamps
- [x] Programmatic Python interface (`SimulatorInterface`)
- [x] Automated test suite passing (7/7 tests)
- [x] CLI control scripts (`start_simulation`, `stop_simulation`, `run_mission`, `reset_simulation`)
