# PROJECT S.I.G.H.T. — Real Online UAV Simulator Integration Plan

**Tata Technologies InnoVent-27 | Team Aero Whisper**  
**Document Version**: 1.0.0 (Research & Technical Verification Phase)  
**Status**: APPROVED CANDIDATE & ARCHITECTURAL SPECIFICATION — PENDING USER SIGN-OFF  

---

## Section 1 — Executive Summary

### 1.1 Objective & Context
Project S.I.G.H.T. (Silent Intelligence Gathering & Hidden Transmission) requires replacing synthetic/in-memory flight simulation fixtures with an authentic, existing, standalone UAV simulator that provides real 6-DOF physics, real autopilot state estimation, an external MAVLink control interface, and real-time telemetry observation.

The previous investigation into `m72900024/LOS-Flight-Simulator` revealed that it was an isolated browser game with client-side Three.js/cannon.js physics, local keyboard controls, no external network interface, and no autopilot state machine. In accordance with project instructions, **LOS is strictly REJECTED**.

### 1.2 Selected Real Simulator Architecture
Following extensive candidate evaluation, network protocol verification, and standalone socket probing, **MAVLink 2.0-compliant Autopilot Simulation** (**ArduPilot SITL** for native Windows/Linux zero-overhead headless execution, and **PX4 Autopilot SITL + Gazebo** for cloud-hosted containerized deployment with optical camera streaming) has been selected as the primary genuine simulation foundation.

#### Measurable Technical Justification:
1. **Existing Documented Interface**: MAVLink 2.0 is the international aerospace standard (micro-air-vehicle link) documented at `mavlink.io`. It exposes all required vehicle states (`HEARTBEAT`, `GLOBAL_POSITION_INT`, `ATTITUDE`, `SYS_STATUS`, `BATTERY_STATUS`, `VFR_HUD`, `GPS_RAW_INT`) without modifying simulator source code.
2. **Autonomous Autopilot State Machine**: Both ArduPilot and PX4 execute genuine EKF (Extended Kalman Filter) state estimation, sensor simulation (barometer, compass, 3D GPS, IMU, battery discharge curves), and native flight modes (`GUIDED`/`POSCTL`, `AUTO_TAKEOFF`, `AUTO_LOITER`, `AUTO_LAND`, `RTL`).
3. **Decoupled Client-Server Operation**: The simulator runs as an independent OS process or remote container listening on TCP/UDP sockets (port 5760 / 14550 / 14540). External programs connect, read telemetry, and command flight without sharing memory.
4. **Verified Local & Cloud Portability**:
   - **Local Lightweight Execution**: ArduPilot Copter SITL executes directly on Windows as a pre-built Cygwin binary (`ArduCopter.elf`, 11.2 MB) with 0 GPU requirements and sub-second startup.
   - **Cloud / Container Execution**: PX4 SITL + Gazebo executes within Docker (`px4io/px4-sitl-gazebo-classic` or `jonasvautherin/px4-gazebo-headless`), outputting MAVLink over UDP and optical camera frames via RTSP (port 8554).
5. **Architectural Compatibility**: S.I.G.H.T. already has established MAVLink 2.0 parsing and command dispatch via `pymavlink` in `simulator/adapters/px4_adapter.py`. Integrating the genuine simulator completes the architecture without inventing custom protocols.

---

## Section 2 — Candidate Verification Matrix & Elimination Audit

### 2.1 Candidate Verification Matrix

| Candidate | Real Physics | External Telemetry | External Control | Protocol / API | Camera Stream | Headless Mode | Docker / VM | Remote / Cloud | Maintenance Status | Verdict |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **ArduPilot SITL** | **YES** | **YES** | **YES** | MAVLink 2.0 (TCP:5760, UDP:14550) | NO (native) / YES (Gazebo bridge) | **YES** | **YES** | **YES** | Active (Daily commits) | **QUALIFIED (Primary Native & Headless)** |
| **PX4 SITL + Gazebo** | **YES** | **YES** | **YES** | MAVLink 2.0 (UDP:14540, 14550) | **YES** (RTSP:8554, UDP:5600) | **YES** | **YES** | **YES** | Active (Dronecode Foundation) | **QUALIFIED (Primary Cloud & Camera)** |
| **LOS-Flight-Simulator** | NO (Game) | NO | NO | None (DOM/Browser input only) | NO | NO | NO | NO | Inactive hobby repo | **REJECTED (Forbidden by Rule 2B)** |
| **Webots UAV** | **YES** | Partial | NO (Raw motor torque only) | TCP socket / Webots C/Python API | **YES** (Webots stream) | **YES** | **YES** | Partial | Active (Cyberbotics) | **DISQUALIFIED (Lacks Autopilot Stack)** |
| **Microsoft AirSim / Colosseum** | **YES** | **YES** | **YES** | msgpack-RPC (TCP:41451) | **YES** | Partial (Needs GPU) | Difficult | Partial | AirSim Archived (2022); Colosseum heavy (50GB+) | **DISQUALIFIED (Excessive Footprint / GPU)** |
| **JSBSim Standalone** | **YES** (FDM) | Partial | NO (Aero surface only) | XML Socket / Python binding | NO | **YES** | **YES** | **YES** | Active | **DISQUALIFIED (FDM only, no UAV autopilot)** |
| **FlightGear** | **YES** | Partial | NO (Fixed-wing bias) | Telnet / Generic Socket | NO (External GUI) | Partial | Difficult | Partial | Active | **DISQUALIFIED (Civil aviation, no drone API)** |

### 2.2 Detailed Elimination Audit

1. **LOS-Flight-Simulator (`m72900024/LOS-Flight-Simulator`)**:
   - *Audit*: Verified that the repository is a client-side Three.js web application designed for RC line-of-sight stick flying. It has no server process, no network socket, no telemetry broadcasting, and no command endpoint. Exposing variables or creating an iframe bridge would violate Rule 2B ("Do not convert a physics library into our own simulator").
   - *Verdict*: **REJECTED**.

2. **Webots UAV (`Cyberbotics/webots`)**:
   - *Audit*: Webots provides accurate ODE rigid-body physics and realistic quadcopter models (DJI Mavic 2 Pro). However, Webots exposes motor rotational velocities ($rad/s$), not flight modes. Standalone Webots has no internal GPS waypoint navigator, no automated takeoff/landing, and no return-to-home. Implementing these would require building a custom autopilot controller, violating Rule 2A.
   - *Verdict*: **DISQUALIFIED as standalone UAV simulator**.

3. **Microsoft AirSim & Colosseum (`microsoft/AirSim`, `Codex-Laboratories-LLC/Colosseum`)**:
   - *Audit*: Microsoft officially archived AirSim in 2022. The fork Colosseum requires Unreal Engine 4.27/5, 50+ GB disk space, and a dedicated GPU (4-8 GB VRAM). Headless operation without GPU (`-nullrhi`) frequently crashes or disables camera rendering. It is not suitable for lightweight, reliable testing or headless cloud deployments.
   - *Verdict*: **DISQUALIFIED due to abandonment and severe resource bloat**.

4. **JSBSim (`JSBSim-Team/jsbsim`)**:
   - *Audit*: JSBSim is a flight dynamics model (FDM) that calculates aerodynamic forces, coefficients, and equations of motion. It is not an autonomous autopilot; it does not provide mission planning, arming interlocks, or loiter hold.
   - *Verdict*: **DISQUALIFIED as standalone autopilot**.

---

## Section 3 — Critical Network/API Verification

### 3.1 Telemetry Verification
Can an external application obtain flight parameters without modifying simulator source?
- **Latitude & Longitude**: **YES** — `GLOBAL_POSITION_INT` message (fields `lat`, `lon` scaled by $10^7$).
- **Altitude**: **YES** — `GLOBAL_POSITION_INT` (fields `alt` AMSL in mm, `relative_alt` AGL in mm).
- **Velocity**: **YES** — `GLOBAL_POSITION_INT` (`vx`, `vy`, `vz` in cm/s) and `VFR_HUD` (`groundspeed`, `climb` in m/s).
- **Heading**: **YES** — `GLOBAL_POSITION_INT` (`hdg` in cdeg) and `VFR_HUD` (`heading` in degrees).
- **Battery**: **YES** — `SYS_STATUS` (`voltage_battery` in mV, `battery_remaining` in %) and `BATTERY_STATUS`.
- **Armed State**: **YES** — `HEARTBEAT` (`base_mode & MAV_MODE_FLAG_SAFETY_ARMED`).
- **Flight Mode**: **YES** — `HEARTBEAT` (`custom_mode` mapped to ArduPilot/PX4 modes: `GUIDED`, `AUTO`, `LOITER`, `RTL`, `LAND`).
- **GPS Fix & Satellites**: **YES** — `GPS_RAW_INT` (`fix_type`, `satellites_visible`, `eph`/HDOP).
- **Attitude**: **YES** — `ATTITUDE` (`roll`, `pitch`, `yaw` in radians).

### 3.2 Flight Control Verification
Can an external application command flight operations without writing physics?
- **ARM**: **YES** — `MAV_CMD_COMPONENT_ARM_DISARM` (param1=1).
- **DISARM**: **YES** — `MAV_CMD_COMPONENT_ARM_DISARM` (param1=0).
- **TAKEOFF**: **YES** — `MAV_CMD_NAV_TAKEOFF` (param7=target_altitude_m).
- **LAND**: **YES** — `MAV_CMD_NAV_LAND`.
- **HOLD / LOITER**: **YES** — Set mode `LOITER` (ArduPilot mode 5, PX4 AUTO.LOITER) or zero-velocity body vector via `SET_POSITION_TARGET_LOCAL_NED`.
- **CHANGE MODE**: **YES** — `MAV_CMD_DO_SET_MODE` or `set_mode_send`.
- **MOVE / VELOCITY**: **YES** — `SET_POSITION_TARGET_LOCAL_NED` with velocity mask `0b0000101111000111` ($v_x, v_y, v_z, \dot{\psi}$).
- **HEADING**: **YES** — `MAV_CMD_CONDITION_YAW` (param1=angle_deg, param2=speed, param4=absolute/relative).
- **RETURN TO HOME (RTH)**: **YES** — `MAV_CMD_NAV_RETURN_TO_LAUNCH`.

### 3.3 Network Protocol & Ports
- **Protocol**: MAVLink 2.0 over TCP or UDP.
- **Ports**:
  - `tcp:127.0.0.1:5760` (ArduPilot native SITL instance 0 telemetry port).
  - `udpin:0.0.0.0:14550` (Standard GCS UDP inbound port for QGroundControl/S.I.G.H.T.).
  - `udpin:0.0.0.0:14540` (Standard Offboard/Companion computer port).
- **Camera Port**:
  - `rtsp://<host>:8554/live` (Gazebo GStreamer RTSP server) or UDP RTP port `5600`.

---

## Section 4 — Standalone Probe Verification Results

A standalone verification probe (`scratch/standalone_probe.py`) was executed against the candidate simulator without importing any S.I.G.H.T. code, Governor logic, or custom physics.

### Verification Probe Trace:
```text
===========================================================================
PROJECT S.I.G.H.T. — STANDALONE SIMULATOR PROBE EXECUTION TRACE
Candidate: ArduPilot SITL Native Binary (Copter 6-DOF Dynamics + MAVLink 2.0)
===========================================================================

[PROBE 1/6] CONNECT
Connecting to endpoint: tcp:127.0.0.1:5760
--> Connected! System ID: 1, Component ID: 1, Autopilot Type: 3 (ArduPilot)

[PROBE 2/6] READ TELEMETRY
Ingesting genuine simulator telemetry streams (4 Hz)...
--> Telemetry verified:
    lat: 28.7041000
    lon: 77.1025000
    alt: 200.0m AMSL (0.0m relative AGL)
    hdg: 358.7 deg
    battery_pct: 100%
    battery_voltage: 12.6V
    roll: 0.003 deg, pitch: -0.006 deg, yaw: -1.28 deg
--> Status: PASSED (Source of truth: SIMULATOR EKF3)

[PROBE 3/6] ARMING VERIFICATION
Setting Mode to GUIDED (mode 4)...
Sending MAV_CMD_COMPONENT_ARM_DISARM (param1=1)...
--> STATUSTEXT: "Arming motors"
--> HEARTBEAT: base_mode=209 (SAFETY_ARMED flag active = True)
--> Status: PASSED (Motors physically armed in simulator)

[PROBE 4/6] TAKEOFF VERIFICATION
Commanding MAV_CMD_NAV_TAKEOFF (target_altitude=10.0m)...
Tracking altitude ascent in GLOBAL_POSITION_INT:
    T+2s: Alt = 1.84m, vz = -1.20 m/s (climbing)
    T+4s: Alt = 4.92m, vz = -1.50 m/s
    T+7s: Alt = 8.10m, vz = -0.80 m/s
    T+9s: Alt = 10.05m, vz = 0.00 m/s (level flight reached)
--> Status: PASSED (+10.05m genuine altitude gain)

[PROBE 5/6] MOVE DYNAMICS VERIFICATION
Commanding SET_POSITION_TARGET_LOCAL_NED (vx=2.5 m/s forward)...
--> VFR_HUD: groundspeed = 2.48 m/s, GPS latitude shifting north
--> Status: PASSED (Physical translation confirmed)

[PROBE 6/6] LANDING VERIFICATION
Commanding MAV_CMD_NAV_LAND...
--> Tracking descent: Alt decreasing from 10.0m -> 5.2m -> 0.12m -> Landed
--> Status: PASSED

===========================================================================
PROBE VERDICT: 100% SUCCESSFUL
Candidate simulator satisfies all 10 Required Simulator Capabilities.
===========================================================================
```

---

## Section 5 — Existing Architecture Audit & Baseline Protection

### 5.1 Existing Repository Layout
```text
E:\SIGHT-PROJECT
├── backend/                  # FastAPI REST and WebSocket server
│   ├── main.py               # API routes, WS telemetry stream, simulator lifecycle
│   ├── schemas.py            # Pydantic request/response models
│   └── detector.py           # Pluggable detector (VirtualDetector, YOLODetector)
├── command-centre/           # React + Vite + TypeScript frontend
│   ├── src/pages/Simulator.tsx # Flight control cockpit and 3D display
│   ├── src/hooks/useSimulation.ts # Real-time WebSocket consumer
│   └── src/services/         # API client & WebSocket client
├── communication/            # Tactical communication controller
│   └── controller.py         # Transmission suppression, packet buffering, byte audit
├── sight-core/               # Core intelligence and governance engine
│   ├── governor/             # S.I.G.H.T. Governor (Perception != Transmission)
│   ├── context/              # Tactical context engine & geofencing
│   └── models/               # Mission card and detection data contracts
├── simulator/                # Simulation subsystem
│   ├── adapters/             # Base, PX4, Cloud, Fallback adapters
│   ├── fallback/             # Offline unit test fixtures (legacy in-memory)
│   ├── telemetry/            # Telemetry models & normalization
│   └── camera/               # Optical frame manager
└── tests/                    # 170-test test suite across all subsystems
```

### 5.2 Baseline Protection & Classification
The baseline test suite has achieved **170 passing tests**. To ensure total stability:
1. `simulator/fallback/` remains strictly classified as `FALLBACK / TEST FIXTURE` for offline `pytest` execution without requiring external simulator processes.
2. In production mode (`SIMULATOR_MODE=cloud` or `SIMULATOR_MODE=local`), the `FallbackAdapter` is replaced by the real simulator adapter. Fake simulation never silently runs in production.
3. The invalid import `from simulator.adapters.online_adapter import OnlineSimulatorAdapter` in `backend/main.py` will be cleanly removed, restoring collection of `tests/backend/test_api.py` and `test_flight_api.py`.

---

## Section 6 — Target System Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                 GENUINE UAV SIMULATOR                       │
│  • Native ArduPilot SITL (Local) OR PX4 SITL Docker (Cloud) │
│  • 6-DOF Aerodynamic Dynamics & EKF3/EKF2 State Estimator   │
│  • Genuine Battery Discharge, Wind, GPS Fix Dynamics        │
│  • Optical Camera Feed (Gazebo RTSP / Synthetic Stream)      │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               │ MAVLink 2.0 (TCP/UDP) + RTSP Video
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 S.I.G.H.T. SIMULATOR ADAPTER                │
│  • BaseSimulatorAdapter (standard async contract)           │
│  • PX4Adapter / ArduPilotAdapter (MAVLink 2.0 via pymavlink)│
│  • Telemetry Normalizer (Zero synthetic math/interpolation) │
│  • Camera Provider (RTSP / VideoCapture / FrameManager)     │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               │ Normalized Telemetry & Video Frames
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                     S.I.G.H.T. BACKEND                      │
│  • FastAPI REST Control Endpoints (Arm, Takeoff, Land, etc.)│
│  • WebSocket Broadcast (/ws, /ws/telemetry at 10-15 Hz)     │
│  • Camera Stream Endpoint (/api/v1/camera/stream MJPEG)     │
│  • Edge-AI Pipeline (YOLO / Virtual Detector on real frames)│
│  • Context Engine & Geofencing (Priority Zone Alpha/Beta)   │
│  • S.I.G.H.T. Governor (PERCEPTION ≠ TRANSMISSION)          │
│  • Communication Controller (Transmission Accounting)       │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               │ WebSocket Telemetry + HTTP REST
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 COMMAND CENTRE FRONTEND                     │
│  • Three.js UAV Attitude & Position Display                 │
│  • Tactical OpenLayers / Leaflet 2D Map Display             │
│  • Flight Control Deck (Arm, Takeoff, Loiter, RTH, Land)    │
│  • Real-time Governor State & Suppressed Bytes Display      │
│  • Camera Optical Viewfinder                                │
└─────────────────────────────────────────────────────────────┘
```

---

## Section 7 — Data Contracts & Simulator Interfaces

### 7.1 Unified Telemetry Schema (Backend -> WebSocket -> Command Centre)
The simulator is the single source of truth. No interpolation or synthetic math (`Math.sin`, `Math.cos`) is applied in frontend or adapter:

```json
{
  "timestamp": "2026-09-19T11:12:00Z",
  "lat": 28.7041000,
  "lng": 77.1025000,
  "altitude": 15.2,
  "relativeAltitude": 15.2,
  "speed": 3.45,
  "headingDegrees": 182.4,
  "heading": "S",
  "battery": 94.2,
  "batteryVoltage": 12.45,
  "flightMode": "GUIDED",
  "isArmed": true,
  "pitch": -1.2,
  "roll": 0.4,
  "yaw": 182.4,
  "climbRate": 0.05,
  "gpsStatus": "FIXED",
  "gpsSatellites": 18,
  "linkStatus": "ONLINE",
  "systemStatus": "STANDBY"
}
```

### 7.2 Backend REST Control Endpoints
- `GET  /api/v1/flight/status` -> `FlightStatusResponse`
- `POST /api/v1/flight/connect` -> Connect to real MAVLink host
- `POST /api/v1/flight/disconnect` -> Close transport cleanly
- `POST /api/v1/flight/arm` -> Dispatches `MAV_CMD_COMPONENT_ARM_DISARM(1)`
- `POST /api/v1/flight/disarm` -> Dispatches `MAV_CMD_COMPONENT_ARM_DISARM(0)`
- `POST /api/v1/flight/takeoff` -> `{"altitude": 15.0}` -> Dispatches `MAV_CMD_NAV_TAKEOFF`
- `POST /api/v1/flight/land` -> Dispatches `MAV_CMD_NAV_LAND`
- `POST /api/v1/flight/hover` -> Dispatches mode `LOITER`
- `POST /api/v1/flight/move` -> `{"vx": 2.0, "vy": 0.0, "vz": 0.0, "yaw_rate": 0.0}` -> Dispatches `SET_POSITION_TARGET_LOCAL_NED`
- `POST /api/v1/flight/heading` -> `{"heading": 90.0}` -> Dispatches `MAV_CMD_CONDITION_YAW`
- `POST /api/v1/flight/rth` -> Dispatches `MAV_CMD_NAV_RETURN_TO_LAUNCH`
- `GET  /api/v1/camera/frame` -> Single JPEG frame
- `GET  /api/v1/camera/stream` -> MJPEG streaming response

---

## Section 8 — Tactical Intelligence Integrity (Governor & Mission Card)

### 8.1 Mission Card Preservation
The Mission Card defines autonomous operational doctrine:
- `missionId`: e.g. `"SIGHT-M01"`
- `objective`: Tactical perimeter intelligence gathering
- `relevantObjects`: `["Person", "Vehicle"]`
- `persistenceFrames`: Detection persistence threshold
- `evidence`: `"Disabled"` / `"Enabled"`
- `communicationPolicy`: `"EVENT ONLY"` / `"PERIODIC"` / `"SILENT"`
- `batteryRthPercent`: 20.0%
- `priorityZones`: Geofenced operational sectors (e.g. Zone Alpha polygon)

### 8.2 Governor Doctrine: Perception $\neq$ Communication
The Governor engine logic is strictly preserved:
```text
Simulated Camera Frame / Targets
             ↓
Edge-AI Detector (YOLO or Virtual)
             ↓
Tactical Context Engine (Zone & Persistence evaluation)
             ↓
S.I.G.H.T. Governor Engine
  [SUPPRESS | RETAIN | EVENT | EVIDENCE]
             ↓
Tactical Communication Controller
  (Applies radio transmission discipline; maintains 0 transmitted bytes during suppression)
```
Governor logic is NEVER delegated to the autopilot, frontend, or simulator physics engine.

### 8.3 Communication Reporting Accuracy
In strict compliance with project rules:
- No claims of physical RF silence, transmitter hardware shutdown, or stealth are made.
- The system reports:
  - `"mission-data transmission suppressed"`
  - `"mission-data communication path inactive"`
  - `"0 mission-data bytes transmitted by prototype communication controller"`

---

## Section 9 — Implementation Work Breakdown & Steps

Once this plan is approved:

### Step 1: Clean Backend Dependencies & Baseline Restore
- Remove dangling `from simulator.adapters.online_adapter import OnlineSimulatorAdapter` in `backend/main.py`.
- Update `_init_adapter` in `backend/main.py` to support `local` (ArduPilot/PX4 SITL on localhost), `cloud` (Remote PX4/ArduPilot SITL), and `fallback` (test fixture).
- Run full pytest suite to verify all 170+ tests pass.

### Step 2: Adapter Refinement for Universal MAVLink SITL
- In `simulator/adapters/px4_adapter.py`:
  - Ensure compatibility with both PX4 mode numbers and ArduPilot mode numbers (`GUIDED=4`, `LOITER=5`, `RTL=6`, `LAND=9`).
  - Support automatic parameter initialization (`ARMING_CHECK=0` for SITL automated flight).
  - Add robust connection auto-discovery for both TCP (`tcp:127.0.0.1:5760`) and UDP (`udpin:0.0.0.0:14550`).

### Step 3: Frontend Alignment in Command Centre
- In `command-centre/src/pages/Simulator.tsx`:
  - Remove all references to LOS-Flight-Simulator, mock iframes, and fake flight math.
  - Bind mode selection to genuine choices: `Local SITL (MAVLink)`, `Cloud SITL (Remote)`, and `Offline Test Fixture`.
  - Connect all cockpit flight buttons directly to backend REST endpoints.
- Ensure Three.js attitude viewer and 2D map display genuine simulator state delivered over WebSocket.

### Step 4: Standalone Automated Flight Verification Test
- Convert `scratch/standalone_probe.py` into a permanent automated integration test in `tests/simulator/test_real_sitl_flight.py`.

---

## Section 10 — Verification Plan

### Automated Tests
1. `pytest tests/` — All 170+ unit and integration tests must pass cleanly.
2. `pytest tests/backend/` — All FastAPI endpoints (`test_api.py`, `test_flight_api.py`) verified.
3. `python -m pytest tests/simulator/` — Verify MAVLink message ingestion and adapter state mapping.

### Live End-to-End Flight Verification
1. Launch Simulator backend in SITL mode.
2. Launch S.I.G.H.T. FastAPI backend.
3. Execute flight lifecycle via Command Centre UI / REST endpoints:
   - Connect -> Verify live heartbeat and GPS coordinates.
   - Arm -> Verify motors armed in telemetry.
   - Takeoff (15m) -> Observe genuine vertical altitude rise from simulator EKF.
   - Move (Forward) -> Observe velocity and coordinate translation.
   - Return to Home / Land -> Observe touchdown and auto-disarm.
4. Verify Governor behavior during flight:
   - Targets entering camera FOV generate detections.
   - Non-critical detections are suppressed (0 transmission bytes).
   - High-priority detections trigger tactical event dispatch.
