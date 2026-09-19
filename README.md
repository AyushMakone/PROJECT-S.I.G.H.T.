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

The repository does **not** currently verify an end-to-end connection to an installed ArduPilot or PX4 SITL process. The default backend mode is `fallback`.

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

The ArduPilot MAVLink adapter is the intended architecture target and is **PLANNED / IMPLEMENTATION TARGET**; no class named `ArduPilotMavlinkAdapter` currently exists. The existing class named `PX4Adapter` is general MAVLink adapter code that contains a `pymavlink` connection, telemetry decoders, and command methods for a configurable endpoint, including ArduPilot mode handling. PX4 support is optional/future and has not been verified here. `CloudAdapter` is configurable remote MAVLink endpoint support, not an implemented cloud simulator. A live external simulator connection was not available during this audit, so this path is **not verified operationally**.

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

**Status: PARTIALLY IMPLEMENTED / NOT YET VERIFIED**

The intended target is an existing ArduPilot SITL process reached through `pymavlink`; the repository does not include the simulator installation or binary. `simulator/adapters/px4_adapter.py` is existing general MAVLink adapter code, despite its filename/class name. It supports TCP/UDP endpoint configuration, heartbeat decoding, telemetry normalization, and command dispatch for an external endpoint. The adapter contains methods for arm, disarm, takeoff, land, move, heading, hover, and return-to-launch. Mission upload is currently a stub returning success rather than performing a MAVLink mission transfer.

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
| ArduPilot MAVLink adapter | PLANNED / IMPLEMENTATION TARGET | No `ArduPilotMavlinkAdapter` class currently exists; existing `PX4Adapter` is general MAVLink adapter code |
| Existing MAVLink adapter interface | IMPLEMENTED as integration code | `PX4Adapter` uses `pymavlink`; live endpoint not verified |
| ArduPilot SITL | PLANNED / NOT YET VERIFIED | No external simulator process is included or running in this audit |
| PX4 SITL | OPTIONAL / NOT VERIFIED | Adapter tables exist, but no live PX4 process was verified |
| Real telemetry | PLANNED / NOT YET VERIFIED | Adapter decoder exists; current default is fallback |
| Real flight control | PLANNED / NOT YET VERIFIED | Commands exist; live command/result verification was skipped |
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
- Real ArduPilot SITL integration as a planned target
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

- Implement and validate the ArduPilot MAVLink adapter target
- Connect and validate an existing ArduPilot SITL instance
- Verify live MAVLink telemetry and flight-command results
- Implement and verify MAVLink mission upload
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
