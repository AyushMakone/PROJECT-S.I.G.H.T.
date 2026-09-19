"""
PROJECT S.I.G.H.T. — FastAPI Backend Application
Phase 4: REST API gateway for Command Centre integration.

Endpoints:
  GET  /api/v1/health
  GET  /api/v1/telemetry
  POST /api/v1/telemetry
  GET  /api/v1/mission
  POST /api/v1/mission
  POST /api/v1/detect
  GET  /api/v1/governor/state
  GET  /api/v1/comm/state
  GET  /api/v1/comm/events
  GET  /api/v1/comm/evidence
  GET  /api/v1/comm/retained
  POST /api/v1/comm/link
  GET  /api/v1/detections
  POST /api/v1/reset
"""

import sys
import os
import time
import uuid

# Ensure project root is importable
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Bootstrap sight_core (hyphen → underscore alias)
import importlib.util as _ilu
_SIGHT_CORE_DIR = os.path.join(_PROJECT_ROOT, "sight-core")

def _bootstrap(pkg_name: str, pkg_dir: str):
    if pkg_name in sys.modules:
        return
    spec = _ilu.spec_from_file_location(pkg_name, os.path.join(pkg_dir, "__init__.py"),
                                         submodule_search_locations=[pkg_dir])
    mod = _ilu.module_from_spec(spec)
    mod.__path__ = [pkg_dir]
    mod.__package__ = pkg_name
    sys.modules[pkg_name] = mod
    spec.loader.exec_module(mod)
    for sub in os.listdir(pkg_dir):
        sub_dir = os.path.join(pkg_dir, sub)
        sub_init = os.path.join(sub_dir, "__init__.py")
        if not os.path.isdir(sub_dir) or not os.path.exists(sub_init):
            continue
        if sub.startswith((".", "_")) or sub == "tests":
            continue
        full = f"{pkg_name}.{sub}"
        if full in sys.modules:
            continue
        s = _ilu.spec_from_file_location(full, sub_init, submodule_search_locations=[sub_dir])
        m = _ilu.module_from_spec(s)
        m.__path__ = [sub_dir]
        m.__package__ = full
        sys.modules[full] = m
        s.loader.exec_module(m)

_bootstrap("sight_core", _SIGHT_CORE_DIR)

import asyncio
import json
import logging
from fastapi import FastAPI, HTTPException, Body, WebSocket, WebSocketDisconnect, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from typing import List, Optional, Dict, Any, Set

from sight_core.models.mission_card import MissionCard, PriorityZone
from sight_core.models.detection import PerceptionDetection
from sight_core.mission.mission_card_manager import MissionCardManager
from sight_core.context.context_engine import ContextEngine
from sight_core.governor.governor_engine import GovernorEngine

from .schemas import (
    DetectionRequest, DetectionResponse, MissionCardRequest, MissionCardResponse,
    TelemetryData, GovernorStateResponse, CommStateResponse, HealthResponse,
    ConnectSimulatorRequest, TakeoffRequest, MoveRequest, HeadingRequest, FlightStatusResponse
)
from .detector import DetectorFactory
from communication.controller import CommunicationController, CommState
from simulator.adapters.base_adapter import BaseSimulatorAdapter
from simulator.adapters.px4_adapter import PX4Adapter
from simulator.adapters.cloud_adapter import CloudAdapter
from simulator.adapters.fallback_adapter import FallbackAdapter
from simulator.telemetry.telemetry_manager import TelemetryManager
from simulator.camera.frame_manager import FrameManager

logger = logging.getLogger("SIGHT.Backend")

# ─────────────────────────────────────────────
#  Application Bootstrap
# ─────────────────────────────────────────────

_START_TIME = time.time()

# Default mission card (Perimeter Surveillance)
_DEFAULT_MISSION = {
    "missionId": "SIGHT-M01",
    "objective": "Perimeter Surveillance",
    "relevantObjects": ["Person", "Vehicle"],
    "persistenceFrames": 2,
    "evidence": "Disabled",
    "communicationPolicy": "EVENT ONLY",
    "batteryRthPercent": 20.0,
    "minConfidencePercent": 60.0,
    "priorityZones": [
        {
            "id": "ZONE-A",
            "name": "Zone Alpha",
            "polygon": [[28.70, 77.10], [28.72, 77.10], [28.72, 77.13], [28.70, 77.13]],
            "description": "North ridge sector",
        }
    ],
}

# Shared state (in-process singletons)
_mission_manager = MissionCardManager()
_mission_manager.load_from_dict(_DEFAULT_MISSION)
_context_engine = ContextEngine(mission_manager=_mission_manager)
_governor = GovernorEngine(context_engine=_context_engine)
_comm_controller = CommunicationController(link_available=True)
_detector = DetectorFactory.create("virtual")
_telemetry_store: TelemetryData = TelemetryData()
_detection_log: List[Dict[str, Any]] = []
_decision_log: List[Dict[str, Any]] = []
_latest_governor_state: Optional[Dict[str, Any]] = None

# Simulator subsystem integration
# SIMULATOR_MODE: 'local' (ArduPilot/PX4 SITL via MAVLink TCP/UDP)
#                 'cloud' (Remote PX4/ArduPilot SITL container)
#                 'fallback' (Offline test fixture — CI/offline dev)
_sim_mode = os.getenv("SIMULATOR_MODE", "fallback").lower()
_sim_adapter: Optional[BaseSimulatorAdapter] = None
_telemetry_mgr: Optional[TelemetryManager] = None
_frame_mgr: FrameManager = FrameManager(max_fps=15)
_ws_clients: Set[WebSocket] = set()

def _init_adapter(
    mode: str = "fallback",
    host: Optional[str] = None,
    port: Optional[int] = None,
    endpoint: Optional[str] = None
) -> BaseSimulatorAdapter:
    """
    Instantiate the appropriate simulator adapter.

    Modes:
      'local'    — ArduPilot/PX4 SITL running locally via MAVLink
                   Default endpoint: tcp:127.0.0.1:5760 (ArduPilot) or udpin:0.0.0.0:14550 (PX4)
      'cloud'    — Remote PX4/ArduPilot SITL container via MAVLink over network
      'fallback' — In-memory offline test fixture (CI / development without simulator)
    """
    global _sim_adapter, _telemetry_mgr
    m = mode.lower()
    if m == "local":
        # ArduPilot SITL default: tcp:127.0.0.1:5760
        # PX4 SITL default:       udpin:0.0.0.0:14550
        conn = endpoint or os.getenv("MAVLINK_ENDPOINT", "tcp:127.0.0.1:5760")
        logger.info(f"[Backend] Initialising LOCAL MAVLink adapter: {conn}")
        _sim_adapter = PX4Adapter(connection_string=conn)
    elif m == "cloud":
        conn = endpoint or os.getenv("MAVLINK_ENDPOINT", f"udpin:0.0.0.0:{port or 14550}")
        logger.info(f"[Backend] Initialising CLOUD MAVLink adapter: host={host} conn={conn}")
        _sim_adapter = CloudAdapter(host=host, port=port, mavlink_endpoint=conn)
    else:
        # fallback — offline in-memory test fixture
        if m not in ("fallback",):
            logger.warning(f"[Backend] Unrecognised SIMULATOR_MODE '{mode}' — using FallbackAdapter (offline dev)")
        else:
            logger.info("[Backend] Initialising FALLBACK adapter (offline test fixture)")
        _sim_adapter = FallbackAdapter(mavlink_port=port or 14550)

    if _telemetry_mgr:
        _telemetry_mgr.set_adapter(_sim_adapter)
    return _sim_adapter

async def _broadcast_ws(message: Dict[str, Any]):
    if not _ws_clients:
        return
    dead = set()
    for ws in list(_ws_clients):
        try:
            await ws.send_json(message)
        except Exception:
            dead.add(ws)
    for ws in dead:
        _ws_clients.discard(ws)

def _on_telemetry_update(telem: Dict[str, Any]):
    global _telemetry_store
    _telemetry_store.lat = telem.get("lat", _telemetry_store.lat)
    _telemetry_store.lng = telem.get("lng", _telemetry_store.lng)
    _telemetry_store.altitude_m = telem.get("altitude", _telemetry_store.altitude_m)
    _telemetry_store.speed_mps = telem.get("speed", _telemetry_store.speed_mps)
    _telemetry_store.heading_deg = telem.get("headingDegrees", _telemetry_store.heading_deg)
    _telemetry_store.battery_percent = telem.get("battery", _telemetry_store.battery_percent)
    _telemetry_store.battery_voltage_v = telem.get("batteryVoltage", _telemetry_store.battery_voltage_v)
    _telemetry_store.is_armed = telem.get("isArmed", _telemetry_store.is_armed)
    _telemetry_store.flight_mode = telem.get("flightMode", _telemetry_store.flight_mode)
    _telemetry_store.timestamp_utc = telem.get("timestamp", _telemetry_store.timestamp_utc)

    try:
        loop = asyncio.get_running_loop()
        if loop.is_running():
            asyncio.create_task(_broadcast_ws({"type": "telemetry", "data": telem}))
    except RuntimeError:
        pass


# ─────────────────────────────────────────────
#  FastAPI App
# ─────────────────────────────────────────────

app = FastAPI(
    title="PROJECT S.I.G.H.T. API",
    description="Silent Intelligence Gathering & Hidden Transmission — Backend Gateway",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────
#  Health
# ─────────────────────────────────────────────

@app.get("/api/v1/health", response_model=HealthResponse, tags=["System"])
@app.get("/health", response_model=HealthResponse, tags=["System"])
def health():
    active_card = _mission_manager.active_card
    return HealthResponse(
        status="OPERATIONAL",
        version="1.0.0",
        components={
            "governor": "ONLINE",
            "mission_card": active_card.mission_id if active_card else "NONE",
            "communication_controller": "ONLINE",
            "detector": _detector.backend_name,
        },
        uptime_s=round(time.time() - _START_TIME, 2),
    )


# ─────────────────────────────────────────────
#  Telemetry
# ─────────────────────────────────────────────

@app.get("/api/v1/telemetry", response_model=TelemetryData, tags=["Telemetry"])
def get_telemetry():
    return _telemetry_store


@app.post("/api/v1/telemetry", tags=["Telemetry"])
def post_telemetry(data: TelemetryData):
    global _telemetry_store
    _telemetry_store = data
    return {"status": "OK"}


# ─────────────────────────────────────────────
#  Mission Card
# ─────────────────────────────────────────────

@app.get("/api/v1/mission", tags=["Mission"])
def get_mission():
    card = _mission_manager.active_card
    if not card:
        raise HTTPException(status_code=404, detail="No active mission card")
    return card.model_dump(by_alias=True)


@app.post("/api/v1/mission", response_model=MissionCardResponse, tags=["Mission"])
def post_mission(req: MissionCardRequest):
    try:
        card_dict = req.model_dump(by_alias=True)
        _mission_manager.load_from_dict(card_dict)
        card = _mission_manager.active_card
        return MissionCardResponse(
            status="OK",
            mission_id=card.mission_id,
            message=f"Mission card '{card.mission_id}' loaded successfully.",
        )
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))


# ─────────────────────────────────────────────
#  Detection → Governor Pipeline
# ─────────────────────────────────────────────

@app.post("/api/v1/detect", response_model=DetectionResponse, tags=["Detection"])
def detect(req: DetectionRequest):
    """
    Submit a detection from the Edge AI layer.
    Runs through S.I.G.H.T. Governor → Communication Controller.
    Returns the governor decision and communication result.
    """
    global _latest_governor_state

    if not _mission_manager.active_card:
        raise HTTPException(status_code=400, detail="No active mission card. POST /api/v1/mission first.")

    # Build PerceptionDetection
    detection = PerceptionDetection(
        id=req.id,
        objectClass=req.object_class,
        confidence=req.confidence,
        normBbox=req.norm_bbox,
        trackId=req.track_id,
        persistence=req.persistence,
        lat=req.lat,
        lng=req.lng,
        altitudeM=req.altitude_m,
        timestamp=req.timestamp,
        frameId=req.frame_id,
    )

    # Governor evaluation
    decision = _governor.evaluate(
        detection=detection,
        uav_battery_percent=_telemetry_store.battery_percent,
        communication_available=_comm_controller.link_available,
    )

    # Communication Controller dispatch
    det_dict = req.model_dump(by_alias=True)
    det_dict["zoneName"] = decision.zone_name
    _comm_controller.process_decision(
        governor_decision=decision.decision,
        governor_reason=decision.reason,
        detection=det_dict,
        mission_id=decision.mission_id,
    )

    # Log
    decision_entry = {
        "decision": decision.decision,
        "reason": decision.reason,
        "action": decision.action,
        "mission_id": decision.mission_id,
        "target_type": decision.target_type,
        "zone_name": decision.zone_name,
        "timestamp": decision.timestamp,
        "evaluated_conditions": decision.evaluated_conditions.model_dump(by_alias=False),
    }
    _decision_log.append(decision_entry)
    _detection_log.append(det_dict)
    _latest_governor_state = decision_entry

    return DetectionResponse(
        detection_id=req.id,
        object_class=req.object_class,
        confidence=req.confidence,
        decision=decision.decision,
        reason=decision.reason,
        action=decision.action,
        mission_id=decision.mission_id,
        zone_name=decision.zone_name,
        timestamp=decision.timestamp,
        evaluated_conditions=decision.evaluated_conditions.model_dump(by_alias=False),
    )


@app.get("/api/v1/detections", tags=["Detection"])
def get_detections(limit: int = 50):
    return _detection_log[-limit:]


# ─────────────────────────────────────────────
#  Governor State
# ─────────────────────────────────────────────

@app.get("/api/v1/governor/state", response_model=GovernorStateResponse, tags=["Governor"])
def governor_state():
    if not _latest_governor_state:
        raise HTTPException(status_code=404, detail="No governor decisions yet")
    return GovernorStateResponse(**_latest_governor_state)


@app.get("/api/v1/governor/history", tags=["Governor"])
def governor_history(limit: int = 100):
    return _decision_log[-limit:]


# ─────────────────────────────────────────────
#  Communication Controller
# ─────────────────────────────────────────────

@app.get("/api/v1/comm/state", response_model=CommStateResponse, tags=["Communication"])
def comm_state():
    stats = _comm_controller.stats
    return CommStateResponse(
        state=_comm_controller.state.value,
        packets_sent=stats.packets_sent,
        bytes_transmitted=stats.bytes_transmitted,
        events_transmitted=stats.events_transmitted,
        evidence_transmitted=stats.evidence_transmitted,
        suppressed=stats.suppressed,
        retained=stats.retained,
        last_transmission_ms=stats.last_transmission_ms,
        link_available=_comm_controller.link_available,
    )


@app.get("/api/v1/comm/events", tags=["Communication"])
def comm_events(limit: int = 100):
    return _comm_controller.get_transmitted_events()[-limit:]


@app.get("/api/v1/comm/evidence", tags=["Communication"])
def comm_evidence(limit: int = 100):
    return _comm_controller.get_transmitted_evidence()[-limit:]


@app.get("/api/v1/comm/retained", tags=["Communication"])
def comm_retained(limit: int = 100):
    return _comm_controller.get_retained_buffer()[-limit:]


@app.post("/api/v1/comm/link", tags=["Communication"])
def set_comm_link(available: bool = Body(..., embed=True)):
    """Toggle mission-data communication link availability."""
    _comm_controller.set_link_available(available)
    return {"status": "OK", "link_available": available}


# ─────────────────────────────────────────────
#  Reset
# ─────────────────────────────────────────────

@app.post("/api/v1/reset", tags=["System"])
def reset_system():
    global _detection_log, _decision_log, _latest_governor_state, _telemetry_store
    _comm_controller.reset_stats()
    _detection_log = []
    _decision_log = []
    _latest_governor_state = None
    _telemetry_store = TelemetryData()
    return {"status": "RESET", "message": "All runtime state cleared. Mission card preserved."}


# ─────────────────────────────────────────────
#  Lifespan Events
# ─────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    global _sim_adapter, _telemetry_mgr
    sim_mode = os.getenv("SIMULATOR_MODE", "fallback").lower()
    _init_adapter(mode=sim_mode)
    if _sim_adapter:
        try:
            connected = await _sim_adapter.connect()
            if connected:
                logger.info(f"[+] Simulator adapter connected: {_sim_adapter.mode_name.upper()}")
            else:
                logger.warning("[+] Simulator adapter not yet connected — waiting for MAVLink heartbeat.")
        except Exception as e:
            logger.warning(f"[+] Simulator connect deferred (SITL host not yet running): {e}")

    _telemetry_mgr = TelemetryManager(adapter=_sim_adapter, rate_hz=10.0)
    _telemetry_mgr.add_listener(_on_telemetry_update)
    await _telemetry_mgr.start()
    logger.info("[+] S.I.G.H.T. Backend Startup Complete. Telemetry pipeline active.")


@app.on_event("shutdown")
async def shutdown_event():
    global _telemetry_mgr, _sim_adapter
    if _telemetry_mgr:
        await _telemetry_mgr.stop()
    if _sim_adapter:
        await _sim_adapter.disconnect()
    logger.info("[+] S.I.G.H.T. Backend Shutdown Complete.")


# ─────────────────────────────────────────────
#  WebSocket Telemetry & Decision Stream
# ─────────────────────────────────────────────

@app.websocket("/ws")
@app.websocket("/ws/telemetry")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    _ws_clients.add(websocket)
    try:
        # Initial greeting with current system state
        telem_payload = _telemetry_store.model_dump()
        card_payload = _mission_manager.active_card.model_dump(by_alias=True) if _mission_manager.active_card else None
        await websocket.send_json({
            "type": "init",
            "telemetry": telem_payload,
            "mission": card_payload,
            "mode": _sim_adapter.mode_name if _sim_adapter else "offline",
            "isConnected": _sim_adapter.is_connected if _sim_adapter else False
        })

        while True:
            text = await websocket.receive_text()
            try:
                msg = json.loads(text)
                if msg.get("action") == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": time.time()})
            except Exception:
                pass
    except WebSocketDisconnect:
        _ws_clients.discard(websocket)
    except Exception:
        _ws_clients.discard(websocket)


# ─────────────────────────────────────────────
#  Flight Control Endpoints
# ─────────────────────────────────────────────

@app.get("/api/v1/flight/status", response_model=FlightStatusResponse, tags=["Flight Control"])
async def flight_status():
    if not _sim_adapter:
        return FlightStatusResponse(
            status="OFFLINE", mode="none", is_connected=False, is_armed=False,
            flight_mode="DISARMED", link_status="LOST", battery_percent=100.0,
            altitude_m=0.0, lat=_telemetry_store.lat, lng=_telemetry_store.lng, message="No simulator adapter"
        )
    telem = await _sim_adapter.get_telemetry()
    return FlightStatusResponse(
        status="CONNECTED" if _sim_adapter.is_connected else "DISCONNECTED",
        mode=_sim_adapter.mode_name,
        is_connected=_sim_adapter.is_connected,
        is_armed=_sim_adapter.is_armed,
        flight_mode=_sim_adapter.flight_mode,
        link_status=telem.get("linkStatus", "ONLINE"),
        battery_percent=telem.get("battery", 100.0),
        altitude_m=telem.get("altitude", 0.0),
        lat=telem.get("lat", 34.0522),
        lng=telem.get("lng", -117.8247),
        message=f"Simulator Mode: {_sim_adapter.mode_name.upper()}"
    )


@app.post("/api/v1/flight/connect", tags=["Flight Control"])
async def flight_connect(req: ConnectSimulatorRequest):
    global _sim_adapter
    _init_adapter(mode=req.mode, host=req.host, port=req.port, endpoint=req.endpoint)
    success = await _sim_adapter.connect()
    await _broadcast_ws({"type": "status", "mode": _sim_adapter.mode_name, "isConnected": success})
    return {"status": "OK" if success else "CONNECTING", "mode": _sim_adapter.mode_name, "isConnected": success}


@app.post("/api/v1/flight/disconnect", tags=["Flight Control"])
async def flight_disconnect():
    if _sim_adapter:
        await _sim_adapter.disconnect()
        await _broadcast_ws({"type": "status", "mode": _sim_adapter.mode_name, "isConnected": False})
    return {"status": "DISCONNECTED"}


@app.post("/api/v1/flight/arm", tags=["Flight Control"])
async def flight_arm():
    if not _sim_adapter:
        raise HTTPException(status_code=400, detail="Simulator not connected")
    success = await _sim_adapter.arm()
    return {"status": "ARMED" if success else "FAILED", "success": success}


@app.post("/api/v1/flight/disarm", tags=["Flight Control"])
async def flight_disarm():
    if not _sim_adapter:
        raise HTTPException(status_code=400, detail="Simulator not connected")
    success = await _sim_adapter.disarm()
    return {"status": "DISARMED" if success else "FAILED", "success": success}


@app.post("/api/v1/flight/takeoff", tags=["Flight Control"])
async def flight_takeoff(req: TakeoffRequest):
    if not _sim_adapter:
        raise HTTPException(status_code=400, detail="Simulator not connected")
    success = await _sim_adapter.takeoff(altitude=req.altitude)
    return {"status": "TAKEOFF_COMMANDED" if success else "FAILED", "altitude_m": req.altitude, "success": success}


@app.post("/api/v1/flight/land", tags=["Flight Control"])
async def flight_land():
    if not _sim_adapter:
        raise HTTPException(status_code=400, detail="Simulator not connected")
    success = await _sim_adapter.land()
    return {"status": "LAND_COMMANDED", "success": success}


@app.post("/api/v1/flight/hover", tags=["Flight Control"])
async def flight_hover():
    if not _sim_adapter:
        raise HTTPException(status_code=400, detail="Simulator not connected")
    success = await _sim_adapter.hover()
    return {"status": "HOVER_COMMANDED", "success": success}


@app.post("/api/v1/flight/move", tags=["Flight Control"])
async def flight_move(req: MoveRequest):
    if not _sim_adapter:
        raise HTTPException(status_code=400, detail="Simulator not connected")
    success = await _sim_adapter.move(vx=req.vx, vy=req.vy, vz=req.vz, yaw_rate=req.yaw_rate)
    return {"status": "MOVE_COMMANDED", "success": success}


@app.post("/api/v1/flight/heading", tags=["Flight Control"])
async def flight_heading(req: HeadingRequest):
    if not _sim_adapter:
        raise HTTPException(status_code=400, detail="Simulator not connected")
    success = await _sim_adapter.set_heading(heading_deg=req.heading)
    return {"status": "HEADING_COMMANDED", "heading": req.heading, "success": success}


@app.post("/api/v1/flight/rth", tags=["Flight Control"])
async def flight_rth():
    if not _sim_adapter:
        raise HTTPException(status_code=400, detail="Simulator not connected")
    success = await _sim_adapter.return_to_home()
    return {"status": "RTH_COMMANDED", "success": success}


# ─────────────────────────────────────────────
#  Camera Endpoints
# ─────────────────────────────────────────────

@app.get("/api/v1/camera/frame", tags=["Camera"])
async def camera_frame():
    if _sim_adapter:
        frame = await _sim_adapter.get_camera_frame()
        if frame is not None:
            _frame_mgr.update_frame(frame)
    jpeg = _frame_mgr.get_latest_jpeg()
    if not jpeg:
        raise HTTPException(status_code=404, detail="No camera frame available from simulator")
    return Response(content=jpeg, media_type="image/jpeg")


@app.get("/api/v1/camera/stream", tags=["Camera"])
async def camera_stream():
    async def frame_generator():
        while True:
            if _sim_adapter:
                frame = await _sim_adapter.get_camera_frame()
                if frame is not None:
                    _frame_mgr.update_frame(frame)
            jpeg = _frame_mgr.get_latest_jpeg()
            if jpeg:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg + b'\r\n')
            await asyncio.sleep(0.1) # 10 FPS

    return StreamingResponse(frame_generator(), media_type="multipart/x-mixed-replace; boundary=frame")


# ─────────────────────────────────────────────
#  Run directly
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=False)

