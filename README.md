# PROJECT S.I.G.H.T.

**Silent Intelligence Gathering & Hidden Transmission**  
**Mission-Aware Communication Governance architecture for UAVs**

> Sense locally. Decide locally. Communicate selectively.
>
> The UAV observes more information than the communication link needs to transmit.

**Tata Technologies InnoVent-27 | Team Aero Whisper**

## Overview

S.I.G.H.T. is a software proof of concept for separating perception from mission-data communication decisions. A detection is evaluated against mission context, then classified as `SUPPRESS`, `RETAIN`, `EVENT`, or `EVIDENCE`.

This repository contains a FastAPI backend, the S.I.G.H.T. core decision engine, a mission-data communication controller, a React/TypeScript Command Centre, simulator adapter interfaces, and a local synthetic fallback simulator.

The repository includes a real `pymavlink` adapter path for ArduPilot/PX4-compatible endpoints and a separate fallback simulator. Live SITL validation is environment-dependent and requires a reachable heartbeat. The normal backend startup script selects `SIMULATOR_MODE=local`; use `fallback` explicitly for offline development.

## Core Principle

**PERCEPTION != COMMUNICATION DECISION**

```text
Edge AI
    identifies what is observed

Mission Context
    determines what matters for the mission

S.I.G.H.T. Governor
    determines what should be communicated

Communication Controller
    determines how mission data is accounted for and dispatched
```

The system governs mission-data communication only. It does not disable flight-control links, provide RF hardware control, measure RF emissions, or provide physical stealth or anti-jamming behavior.

## Architecture

### Intended ArduPilot-first path

```text
REAL ARDUPILOT SITL
        |
        | MAVLink over TCP or UDP
        v
ArduPilot MAVLink Adapter
        |
        v
S.I.G.H.T. Backend
        |
    | WebSocket
        v
Ground Command Centre
```

No class named `ArduPilotMavlinkAdapter` exists. The existing `PX4Adapter` is general MAVLink adapter code with a `pymavlink` connection, telemetry decoders, command methods, and ArduPilot mode handling for a configurable endpoint. `CloudAdapter` is configurable remote MAVLink endpoint support, not a supplied cloud simulator. Live external SITL verification remains environment-dependent.

MAVLink is an open lightweight messaging protocol widely used in UAV and autopilot ecosystems.

### Implemented decision path

```text
Detection request
    -> ContextEngine
    -> GovernorEngine
    -> CommunicationController
    -> REST response and runtime logs
```

### Governor states

- **SUPPRESS**: discard an irrelevant detection at the decision layer; no mission-data packet is created.
- **RETAIN**: keep detection metadata in the in-process retention buffer when communication or mission criteria do not permit transmission.
- **EVENT**: create and account for a compact event-metadata packet.
- **EVIDENCE**: create and account for a packet containing metadata and ROI fields when the mission policy requires evidence.

These states describe software decisions and packet accounting. They do not prove physical transmitter shutdown or any measured RF behavior.

## System Components

### Real UAV simulator integration

**Status: IMPLEMENTED ADAPTER PATH / LIVE SITL VERIFICATION ENVIRONMENT-DEPENDENT**

The adapter reaches an existing ArduPilot SITL process through `pymavlink`; the repository does not include the simulator installation or binary. `simulator/adapters/px4_adapter.py` supports TCP/UDP endpoint configuration, heartbeat decoding, telemetry normalization, command dispatch, and the MAVLink mission-upload handshake. It contains methods for arm, disarm, takeoff, land, move, heading, hover, return-to-launch, and mission upload. A successful mission upload requires the actual `MISSION_ACK` from the connected vehicle.

The test suite contains live-SITL tests, but they are skip-gated when the configured endpoint is unreachable. No live SITL connection was verified in this audit.

### Simulator fallback

**Status: FALLBACK / TEST ONLY**

`simulator/fallback/` and `FallbackAdapter` implement an in-memory kinematic state machine, synthetic world entities, synthetic camera frames, and local command behavior. `simulator/px4/autopilot_state.py` and `simulator/px4/mavlink_server.py` are also repository-owned synthetic simulation components: they calculate simulated vehicle dynamics and emit MAVLink-shaped packets from that state. They are not ArduPilot or PX4 SITL.

The backend selects this path by default with `SIMULATOR_MODE=fallback`. This is **fallback != real simulator** and must not be used as evidence of real SITL integration or described as the primary real UAV simulator.

### Edge AI

**Status: PARTIALLY IMPLEMENTED**

`backend/detector.py` provides:

- `VirtualDetector`, the default backend, which converts synthetic world targets into detection records and adds simulated confidence and bounding-box noise. It performs no ML inference.
- `YOLODetector`, an optional Ultralytics integration. It maps COCO classes to `Person`, `Vehicle`, `Animal`, `Aircraft`, and `Vessel` when a model is available. It returns no detections when the model cannot be loaded, and the factory falls back to `VirtualDetector` when YOLO is requested but unavailable.

The backend has a verified detection-ingestion route into the Governor. A verified production YOLO run on a real camera stream is not present in this audit.

### Camera pipeline

**Status: FALLBACK / PARTIAL**

The fallback adapter generates OpenCV frames from synthetic world entities. `FrameManager` can cache, resize, JPEG-encode, and expose frames; `CameraStream` can read an externally configured OpenCV-compatible URL such as RTSP or HTTP. The backend exposes camera frame and multipart stream routes.

The repository does not contain a verified ArduPilot camera configuration, RTSP source, or evidence that Edge AI is consuming a real external simulator camera. The external camera interface exists, but its source is not currently verified. Simulator telemetry and camera frames are separate paths:

```text
REAL ARDUPILOT TELEMETRY -> MAVLink Adapter

REAL SIMULATOR CAMERA / EXTERNAL VIDEO SOURCE -> Camera Provider -> Edge AI
```

### Mission Card and Mission Context

**Status: IMPLEMENTED in backend/core; frontend workflow PARTIAL**

Pydantic models and `MissionCardManager` support:

- mission ID, objective, and UAV ID
- relevant object classes
- persistence frame threshold
- priority-zone polygons
- evidence policy: `Enabled`, `Disabled`, or `On-Demand`
- communication policy: `EVENT ONLY`, `EVENT & EVIDENCE`, `SILENT`, or `ADAPTIVE`
- battery RTH threshold
- minimum confidence threshold

`POST /api/v1/mission` validates and activates a card. The Command Centre has a Mission view and mission-card components, but this audit does not verify every operator editing workflow as a live backend workflow; mock state remains present in the frontend.

### S.I.G.H.T. Governor

**Status: IMPLEMENTED and unit/integration tested**

`GovernorEngine` applies this verified order:

1. Communication unavailable -> `RETAIN`
2. Battery at or below the RTH threshold -> `RETAIN`
3. Irrelevant object -> `SUPPRESS`
4. Confidence below threshold -> `RETAIN`
5. Outside a priority zone -> `RETAIN`
6. Persistence threshold unmet -> `RETAIN`
7. Evidence required -> `EVIDENCE`
8. Otherwise -> `EVENT`

`ContextEngine` supplies the evaluated conditions using Mission Card values, battery, link availability, geofencing, class relevance, confidence, persistence, and evidence policy.

### Communication Controller

**Status: IMPLEMENTED as software packet governance/accounting**

`communication/controller.py` handles `SUPPRESS`, `RETAIN`, `EVENT`, and `EVIDENCE`, maintains an `INACTIVE -> ACTIVATE -> TRANSMIT -> VERIFY` state model, stores retained detections, creates event/evidence metadata records, and tracks packet counts, bytes, simulated latency, suppressed items, and retained items.

This is not a physical radio driver. Terms such as “mission-data transmission suppressed” or “mission-data communication path inactive” are appropriate; physical RF, transmitter invisibility, and RF measurements are out of scope.

### Backend

**Status: IMPLEMENTED**

The FastAPI application in `backend/main.py` provides:

- REST health, telemetry, Mission Card, detection, Governor, communication, reset, flight-control, and camera routes
- `/ws` and `/ws/telemetry` WebSocket routes
- WebSocket messages for initialization, telemetry, status, Governor, and communication updates where the corresponding runtime path emits them
- in-process runtime state; no database or authentication layer is configured

Flight-control routes call the selected adapter. In fallback mode they control the synthetic adapter; in local/cloud mode they call the MAVLink adapter.

### Command Centre

**Status: IMPLEMENTED UI with live integration paths and local mock fallback**

The Vite/React/TypeScript application includes Dashboard, Mission, Map, AI Events, Governor, Communications, Telemetry, Evidence, Simulator, and Settings routes. It contains WebSocket and REST clients, simulator mode selection, telemetry display, Governor and communication panels, camera URLs, and flight-control actions.

`command-centre/src/services/mock/simulationEngine.ts` and static mock data provide local browser-only telemetry and event behavior. Therefore UI data must be classified as **REAL BACKEND/SIMULATOR DATA only when connected**, otherwise **LOCAL MOCK / FALLBACK TELEMETRY**. Three.js components, where present, are visualization layers only; they are not the source of flight physics or UAV state.

## Backend API Surface

Verified route groups include:

| Group | Routes |
|---|---|
| Health | `GET /health`, `GET /api/v1/health` |
| Telemetry | `GET` and `POST /api/v1/telemetry` |
| Mission | `GET` and `POST /api/v1/mission` |
| Detection | `POST /api/v1/detect`, `GET /api/v1/detections` |
| Governor | `GET /api/v1/governor/state`, `GET /api/v1/governor/history` |
| Communication | `GET /api/v1/comm/state`, `/events`, `/evidence`, `/retained`; `POST /api/v1/comm/link` |
| Flight control | `GET /api/v1/flight/status`; `POST /api/v1/flight/connect`, `/disconnect`, `/arm`, `/disarm`, `/takeoff`, `/land`, `/hover`, `/move`, `/heading`, `/rth` |
| Camera | `GET /api/v1/camera/frame`, `GET /api/v1/camera/stream` |
| Runtime | `POST /api/v1/reset` |

## Repository Structure

```text
backend/             FastAPI gateway, schemas, detector abstraction
communication/       Mission-data packet controller and accounting
command-centre/      React, TypeScript, Vite Command Centre
docs/                Architecture and simulator planning documents
edge-ai/             Edge-AI documentation area
missions/            JSON Mission Card examples
sight-core/          Mission models, context, geofence, Governor
simulator/           Adapter interfaces, fallback engine, camera and telemetry code
tests/               Backend, communication, integration, core, and simulator tests
README.md            This authoritative repository status
```

## Current Implementation Status

| Component | Status | Evidence / boundary |
|---|---|---|
| Command Centre | IMPLEMENTED / PARTIAL LIVE DATA | React routes, REST/WebSocket clients, mock fallback |
| FastAPI backend | IMPLEMENTED | `backend/main.py` routes and runtime services |
| S.I.G.H.T. Core | IMPLEMENTED | Context, geofence, Mission Card, Governor modules |
| Mission Card | IMPLEMENTED in core/backend | Pydantic model and mission endpoints |
| Governor | IMPLEMENTED | Eight-rule decision order and tests |
| Communication Controller | IMPLEMENTED | Packet records, retention, counters, simulated latency |
| Edge AI | PARTIALLY IMPLEMENTED | Virtual detector default; optional YOLO integration |
| ArduPilot MAVLink adapter | IMPLEMENTED integration path | Existing `PX4Adapter` is general MAVLink adapter code; no separate ArduPilot-named class exists |
| Existing MAVLink adapter interface | IMPLEMENTED as integration code | `PX4Adapter` uses `pymavlink`; live endpoint not verified |
| ArduPilot SITL | EXTERNAL / NOT INCLUDED | Start an installed SITL process separately and verify its heartbeat |
| PX4 SITL | OPTIONAL / NOT VERIFIED | Adapter tables exist, but no live PX4 process was verified |
| Real telemetry | PLANNED / NOT YET VERIFIED | Adapter decoder exists; current default is fallback |
| Real flight control | IMPLEMENTED command path / live verification pending | Commands use the adapter when `SIMULATOR_MODE=local` and a reachable MAVLink endpoint is configured |
| MAVLink mission upload | IMPLEMENTED protocol path / live verification pending | `MISSION_COUNT`, mission requests, `MISSION_ITEM_INT`, and `MISSION_ACK` |
| Camera pipeline | PARTIAL / FALLBACK | Synthetic frames and external stream reader; real source not verified |
| WebSocket integration | IMPLEMENTED | `/ws` and `/ws/telemetry` routes plus frontend client |
| Remote MAVLink endpoint | CONFIGURATION PATH ONLY | `CloudAdapter` wraps a configurable endpoint; no remote simulator service is supplied or verified |
| Comparative reduction results | NOT PRESENT | No measured experiment or percentage is stored in the repository |

## Testing and Validation

The audit command was:

```powershell
python -m pytest -q
```

Result during this audit: **185 passed, 6 skipped, 5 warnings**.

The skipped tests include the live ArduPilot SITL flight sequence because `tcp:127.0.0.1:5760` was not reachable. The independent Connect -> HEARTBEAT -> telemetry -> arm -> armed-state -> takeoff -> altitude -> move -> position/velocity -> land -> landed-state probe was not run against a real ArduPilot SITL process during this audit. Passing simulator tests cover repository-owned fallback kinematics, synthetic camera behavior, adapter contracts, and the local MAVLink packet broadcaster; they do not establish that an external ArduPilot or PX4 SITL process is connected.

The test suite includes core Governor, geofence, and Mission Card tests; communication-controller tests; backend API and flight-route tests; integration pipeline tests; fallback simulator tests; and skip-gated live-SITL tests.

## Metrics and Evaluation

The Communication Controller records bytes transmitted, packet count, event count, evidence count, retained count, suppressed count, processed count, and simulated transmission latency. These are software counters, not RF measurements.

The intended comparison is:

```text
Continuous video
vs.
Confidence-threshold events
vs.
S.I.G.H.T. governed mission-data packets
```

```text
Reduction (%) = (Baseline - S.I.G.H.T.) / Baseline * 100
```

No controlled simulator experiment or measured reduction percentage is present in the repository. Quantitative reduction results will be reported after that experiment is completed.

## Deployment Architecture

Local development supports a FastAPI process, a Vite development server, and the repository fallback simulator. The backend also accepts `SIMULATOR_MODE=local`, `SIMULATOR_MODE=cloud`, and `MAVLINK_ENDPOINT` configuration for external adapters.

```text
Vercel or another static frontend host (not configured here)
    |
    v
Frontend / Command Centre

Separate persistent backend host (not supplied)
    |
    v
S.I.G.H.T. Backend

Separate simulator host/process (not supplied)
    |
    v
REAL ARDUPILOT SITL
```

Vercel deployment, a persistent backend, and a remote ArduPilot simulator are **PLANNED / NOT VERIFIED**. Vercel should not be treated as the host for a persistent UAV simulator.

## Local Development

Install the Python dependencies used by the repository, then run the backend from the repository root:

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Run the Command Centre separately:

```powershell
cd command-centre
npm install
npm run dev
```

Run tests from the repository root with `python -m pytest -q`. To exercise the real-SITL test path, start a compatible external simulator and configure `MAVLINK_ENDPOINT`; the live test will otherwise be skipped.

The backend default is `SIMULATOR_MODE=fallback`. Use `SIMULATOR_MODE=local` or `SIMULATOR_MODE=cloud` only when a compatible external MAVLink endpoint is actually available.

## Scope and Limitations

### In scope

- Software simulation and fallback testing
- Real ArduPilot SITL integration through the external MAVLink adapter, pending live environment verification
- External simulator adapter interfaces where implemented
- MAVLink parsing and command-dispatch code where implemented
- Mission Cards, context, geofencing, and deterministic governance
- Optional Edge-AI detector integration
- Selective mission-data packet generation and accounting
- Command Centre visualization and automated tests

### Out of scope

- RF hardware validation or physical transmitter testing
- Anti-jamming, stealth communications, or physical RF invisibility
- Hardware UAV deployment and outdoor flight validation
- Replacement of military command-and-control or autopilot systems
- Claims about measured RF reduction without an experiment

## Current Implementation vs Roadmap

### Current implementation

The verified current implementation is the software Governor and Mission Card pipeline, FastAPI REST/WebSocket gateway, communication accounting controller, fallback simulator and synthetic camera, optional detector interfaces, Command Centre UI, and automated test suite described above.

### Roadmap: PLANNED / NOT YET IMPLEMENTED OR VERIFIED

- Connect and validate an existing ArduPilot SITL instance
- Verify live MAVLink telemetry and flight-command results
- Verify MAVLink mission upload against live ArduPilot SITL
- Connect a real simulator camera or documented external video source
- Run Edge AI inference on that real camera stream
- Complete live end-to-end simulator-to-Command-Centre validation
- Run controlled communication experiments and report measured metrics
- Deploy a persistent remote backend and simulator
- Add production authentication, encryption, and deployment configuration

## Project Identity

**PROJECT S.I.G.H.T.**  
**Silent Intelligence Gathering & Hidden Transmission**  
**Tata Technologies InnoVent-27**  
**Team: Aero Whisper**

S.I.G.H.T. is a mission-aware software architecture: **sense locally, decide locally, communicate selectively**.

## Requirements

- Windows development environment with PowerShell.
- Python 3.12 or newer is expected by the startup script; the checked environment uses Python 3.12.
- Node.js and npm for the Vite Command Centre. The repository does not pin a Node.js version in `package.json`; use a current LTS release.
- Optional WSL2/Ubuntu installation for building and running ArduPilot SITL.
- `pymavlink`, FastAPI, Uvicorn, Pydantic, NumPy, OpenCV, and the other Python dependencies installed in the active environment.
- Frontend dependencies are declared in `command-centre/package.json`, including React 19, Leaflet 1.9, Three.js, TypeScript, Vite, and Tailwind CSS.
- An external ArduPilot SITL installation is required for real MAVLink verification. The repository does not include the SITL binary.

## Installation

### Windows and Python

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```

The repository has no root `requirements.txt`. Use the existing project virtual environment, or install the backend imports required by your selected runtime, including FastAPI, Uvicorn, Pydantic, NumPy, OpenCV, and `pymavlink`. Then install frontend packages:

```powershell
cd command-centre
npm install
cd ..
```

The `sight-core/pyproject.toml` declares the core package requirement `pydantic>=2.0`. Verify the environment with `python -m compileall` and the test suite.

### WSL2 and ArduPilot

Install ArduPilot and its Ubuntu build dependencies in WSL2 according to the ArduPilot documentation. Build or locate `ArduCopter`, then either run SITL from WSL or set `ARDUPILOT_SITL_PATH` to a Windows-accessible directory containing the binary. The helper script expects `udp:127.0.0.1:14550` by default.

## How To Start

The supported PowerShell helper starts three processes:

```powershell
.\scripts\start-all.ps1
```

Or use separate terminals:

```powershell
# Terminal 1: external ArduPilot SITL, or .\scripts\start-sitl.ps1 when ARDUPILOT_SITL_PATH is configured
# Terminal 2
.\scripts\start-backend.ps1
# Terminal 3
.\scripts\start-frontend.ps1
```

The backend is served at `http://127.0.0.1:8000` and the Vite frontend at `http://localhost:5173`.

The backend startup script sets `SIMULATOR_MODE=local`. For offline development only:

```powershell
$env:SIMULATOR_MODE = "fallback"
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

## Real ArduPilot SITL

The real path is:

```text
ArduPilot SITL -> MAVLink -> PX4Adapter -> FastAPI -> Command Centre
```

The adapter accepts TCP or UDP endpoints through `MAVLINK_ENDPOINT`; the normal local default is `udp:172.30.16.1:14550`, while `scripts/start-sitl.ps1` defaults to `udp:127.0.0.1:14550`. Confirm the actual endpoint used by the SITL/MAVProxy bridge before connecting. Verify a heartbeat with MAVProxy or the live-SITL tests before sending commands. Starting the Command Centre does not automatically ARM or TAKEOFF the vehicle.

## Manual Flight Test

At the MAVProxy `MAV>` prompt, use the operator-controlled sequence:

```text
mode GUIDED
arm throttle
takeoff 20
mode LOITER
mode LAND
```

The Command Centre follows the same real command path when connected. TAKEOFF requires telemetry-confirmed ARM and must not silently auto-arm. Uploading a mission does not ARM, TAKEOFF, select AUTO, or start flight.

## Command Centre Sections

- **Dashboard**: operational monitoring, telemetry, detections, Governor state, timeline, and a clean operational map. It has no mission-authoring toolbar.
- **Tactical Map**: the full Leaflet mission-authoring view. The map is followed by the Mission Editor and a single waypoint/hot-zone inspector.
- **Simulation**: operator flight-control and telemetry console.
- **Mission Card**: mission configuration and authoritative Mission Card data.
- **Governor**: `SUPPRESS`, `RETAIN`, `EVENT`, and `EVIDENCE` decisions.
- **Communication**: Communication Controller state, retained data, events, evidence, and software counters.
- **Camera**: camera frame/stream and detection visualization when a provider is available.

## Tactical Map User Guide

1. Open the Tactical Map route at `/map`.
2. Click **EDIT MISSION**.
3. Click **ADD WAYPOINT**, then click the Leaflet map to place WP1. Repeat for WP2 and WP3.
4. Select a waypoint to inspect or edit its altitude, or delete it from the inspector below the map.
5. Click **ADD HOT ZONE**, use the existing map point interaction, and finish the polygon.
6. Select the zone below the map to edit its name, priority, active state, or delete it.
7. Click **SAVE MISSION**. The backend validates and stores the Mission Card, then the frontend reloads the authoritative result.
8. Use **UPLOAD TO UAV** only after the UAV/SITL connection is available.

**SAVE MISSION** persists the local authoritative Mission Card. **UPLOAD TO UAV** is a separate MAVLink transfer to the vehicle and does not start flight.

## MAVLink Mission Upload

The adapter uses the real mission protocol:

```text
MISSION_COUNT
    -> MISSION_REQUEST_INT or MISSION_REQUEST
    -> MISSION_ITEM_INT for each waypoint
    -> MISSION_ACK
```

Upload is rejected when SITL is disconnected, no waypoints exist, or waypoint coordinates/altitudes are invalid. The UI reports success only after the adapter receives `MISSION_ACK`; a timeout or missing ACK is not reported as success. Live ArduPilot ACK verification remains dependent on a reachable SITL instance.

## Perception and Communication

The detector factory supports the default `VirtualDetector` and optional Ultralytics `YOLODetector`; tracking, persistence, Mission Context, Governor decisions, and Communication Controller accounting are separate stages. Current detector settings include `SIGHT_DETECTOR_BACKEND`, `SIGHT_YOLO_MODEL_PATH`, `SIGHT_ALLOW_DETECTOR_FALLBACK`, `SIGHT_YOLO_DEVICE`, `SIGHT_YOLO_CONFIDENCE`, `SIGHT_TRACK_IOU_THRESHOLD`, and `SIGHT_TRACK_MAX_MISSED_FRAMES`.

The Governor decides whether a detection is `SUPPRESS`, `RETAIN`, `EVENT`, or `EVIDENCE`. The Communication Controller converts that decision into software packet/accounting behavior and exposes packet, byte, event, evidence, retained, suppressed, and simulated-latency metrics. These are not RF measurements.

## Testing

```powershell
python -m compileall -q backend simulator sight-core communication
python -m pytest -q
cd command-centre
npm run build
npm run lint
```

The `sitl`-marked tests require a reachable external ArduPilot/PX4 SITL process. Passing fallback and adapter tests do not prove real SITL connectivity. Real verification must explicitly record the SITL endpoint, heartbeat, commands issued, telemetry observed, and mission `MISSION_ACK`.

## Troubleshooting

- **Backend does not start**: activate `.venv`, verify Python dependencies, and run `python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000` directly.
- **Frontend does not start**: run `npm install` in `command-centre`, then `npm run dev -- --host 127.0.0.1 --port 5173`.
- **Tactical Map is blank**: confirm the `/map` route is open, the browser console has no Leaflet error, and the map has its explicit responsive height. Tile loading also requires network access to the configured tile provider.
- **UAV telemetry unavailable**: confirm a heartbeat, `SIMULATOR_MODE=local`, and the `MAVLINK_ENDPOINT`/SITL port match.
- **SITL not connecting**: verify the endpoint with MAVProxy, confirm UDP forwarding or TCP listening, and run `pytest -m sitl` only after SITL is running.
- **TAKEOFF rejected**: connect first, ARM, wait for telemetry to confirm `isArmed`, and use a valid altitude. The system intentionally does not auto-arm.
- **Mission upload rejected**: verify the Mission Card has valid waypoints, the vehicle is connected, and inspect the returned ACK or timeout message.
- **Map tiles not loading**: check internet access and browser network/CSP errors; the map can still display overlays without tiles but will not be a usable basemap.
- **Camera unavailable**: inspect `/api/v1/camera/status` and confirm a simulator camera provider or external stream is configured.
- **YOLO unavailable**: inspect `/api/v1/detector/status`, install Ultralytics/model dependencies if desired, or use the documented Virtual Detector fallback.

## Current Limitations

- ArduPilot SITL is external software; no hardware UAV, RF, or outdoor flight validation is included.
- The synthetic fallback camera and Virtual Detector are not evidence of real camera or YOLO performance.
- Target geolocation is limited by the available telemetry/detection location source.
- Mission upload is implemented, but live `MISSION_ACK` verification remains environment-dependent.
- No RF invisibility, anti-jamming, guaranteed stealth, or fixed communication-reduction percentage is claimed.

## Stage-2 Demo Procedure

1. Start ArduPilot SITL and confirm a heartbeat.
2. Start the backend, then the Command Centre.
3. Verify connection and telemetry.
4. Open Tactical Map, create waypoints and a hot zone, save the Mission Card, and upload it to the UAV.
5. Open Simulation, then manually ARM and TAKEOFF.
6. Observe real telemetry, then manually use LOITER, LAND, or RTL.
7. Show Governor decisions, Communication Controller state, and camera/detection output.
#   P R O J E C T - S . I . G . H . T .  
 