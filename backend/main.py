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
    ConnectSimulatorRequest, TakeoffRequest, MoveRequest, HeadingRequest, FlightStatusResponse,
    FlightCommandResponse
)
from .detector import YOLODetector, VirtualDetector, normalize_world_targets
from .mavlink.events import build_connection_event, build_telemetry_event, build_governor_event, build_communication_event
from .mavlink.parameters import list_parameters, get_parameter, set_parameter
from communication.controller import CommunicationController, CommState
from simulator.adapters.base_adapter import BaseSimulatorAdapter
from simulator.adapters.px4_adapter import PX4Adapter
from simulator.adapters.cloud_adapter import CloudAdapter
from simulator.adapters.fallback_adapter import FallbackAdapter
from simulator.telemetry.telemetry_manager import TelemetryManager
from simulator.camera.frame_manager import FrameManager
from simulator.camera.synthetic_camera_provider import SyntheticCameraProvider

logger = logging.getLogger("SIGHT.Backend")
logger.setLevel(logging.INFO)

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
_detector = None
_detector_status: Dict[str, Any] = {
    "configuredDetector": "virtual",
    "activeDetector": "none",
    "fallback": False,
    "reason": "Not initialized",
    "modelPath": None,
    "modelFound": None,
    "modelLoaded": False,
    "inferenceReady": False,
    "runtimeAvailable": False,
    "runtime": "UNKNOWN",
    "device": None,
}
_perception_frame_id = 0
_perception_last_inference = 0.0
_perception_inference_interval_s = max(0.1, float(os.getenv("SIGHT_VIRTUAL_INFERENCE_INTERVAL_S", "1.0")))
_perception_listener_registered = False
_perception_clock = time.monotonic
_telemetry_store: Optional[TelemetryData] = None
_detection_log: List[Dict[str, Any]] = []
_decision_log: List[Dict[str, Any]] = []
_flight_command_log: List[Dict[str, Any]] = []
_latest_governor_state: Optional[Dict[str, Any]] = None
_runtime_state = {
    "runtime": "ardupilot_sitl",
    "connection_state": "DISCONNECTED",
    "heartbeat_received": False,
    "connected": False,
    "connection": "udp:172.30.16.1:14550",
    "system_id": None,
    "component_id": None,
    "autopilot": None,
    "vehicle": None,
    "armed": None,
    "mode": None,
    "latitude": None,
    "longitude": None,
    "altitude": None,
    "relative_altitude": None,
    "ground_speed": None,
    "heading": None,
    "roll": None,
    "pitch": None,
    "yaw": None,
    "battery": None,
    "gps_fix": None,
    "satellites": None,
    "timestamp": None,
}
_world_entities = [
    {"id": "person-001", "type": "person", "position": [18.5204, 73.8567, 0.0], "heading": 90.0, "velocity": 1.2, "scenario": "perimeter"},
    {"id": "person-002", "type": "person", "position": [18.5212, 73.8574, 0.0], "heading": 120.0, "velocity": 0.8, "scenario": "perimeter"},
    {"id": "vehicle-001", "type": "vehicle", "position": [18.5210, 73.8570, 0.0], "heading": 180.0, "velocity": 2.4, "scenario": "road"},
]
_failure_state = {"gps_loss": False, "camera_failure": False, "mavlink_failure": False, "communication_outage": False, "low_battery": False, "high_wind": False, "sensor_failure": False}
_camera_state = {"status": "NOT CONNECTED", "online": False, "fps": None, "fov": None, "resolution": None}


def _refresh_camera_state_from_adapter() -> Dict[str, Any]:
    global _camera_state
    adapter = _sim_adapter
    connected = bool(adapter and getattr(adapter, "is_connected", False))
    provider = getattr(adapter, "_camera_provider", None) if adapter else None
    sensor = getattr(provider, "sensor", None) if provider else None

    fallback_camera = getattr(adapter, "camera", None) if adapter else None
    if connected and fallback_camera is not None:
        _camera_state = {
            "status": "CONNECTED",
            "online": True,
            "fps": getattr(fallback_camera, "fps", None),
            "fov": f"{getattr(fallback_camera, 'hfov_deg', 75.0):.0f}x{getattr(fallback_camera, 'vfov_deg', 55.0):.0f}",
            "resolution": f"{getattr(fallback_camera, 'width', 640)}x{getattr(fallback_camera, 'height', 480)}",
        }
        return dict(_camera_state)

    if connected and provider is not None and sensor is not None:
        _camera_state = {
            "status": "CONNECTED",
            "online": True,
            "fps": getattr(sensor, "fps", None),
            "fov": f"{getattr(sensor, 'hfov_deg', 75.0):.0f}x{getattr(sensor, 'vfov_deg', 55.0):.0f}",
            "resolution": f"{getattr(sensor, 'width', 640)}x{getattr(sensor, 'height', 480)}",
        }
    else:
        _camera_state = {"status": "NOT CONNECTED", "online": False, "fps": None, "fov": None, "resolution": None}
    return dict(_camera_state)


def _normalize_runtime_mode(mode: Optional[str]) -> str:
    """Normalize runtime mode selection. The real workstation path is local ArduPilot SITL."""
    if mode is None:
        return "local"
    normalized = str(mode).strip().lower()
    if normalized in {"local", "real", "ardupilot", "ardupilot_sitl", "sitl"}:
        return "local"
    if normalized in {"cloud", "remote", "remote_sitl"}:
        return "cloud"
    if normalized in {"fallback", "offline", "mock", "demo"}:
        return "fallback"
    return "local"


def _refresh_runtime_state_from_adapter() -> Dict[str, Any]:
    global _runtime_state
    adapter = _sim_adapter
    connected = bool(adapter and getattr(adapter, "is_connected", False))
    state = dict(_runtime_state)
    state.update({
        "connected": connected,
        "connection_state": "CONNECTED" if connected else "DISCONNECTED",
        "heartbeat_received": connected,
        "system_id": getattr(adapter, "target_system", None) if connected else None,
        "component_id": getattr(adapter, "target_component", None) if connected else None,
        "autopilot": "ArduPilot" if connected and getattr(adapter, "autopilot_type", 0) == 3 else "PX4" if connected and getattr(adapter, "autopilot_type", 0) == 12 else _runtime_state.get("autopilot"),
        "vehicle": "ArduCopter" if connected and getattr(adapter, "vehicle_type", None) == 2 else _runtime_state.get("vehicle"),
        "armed": getattr(adapter, "is_armed", _runtime_state.get("armed")),
        "mode": getattr(adapter, "flight_mode", _runtime_state.get("mode")),
    })
    _runtime_state = state
    return dict(state)


def _flight_state() -> str:
    """Derive safety state from live adapter telemetry, never from UI intent."""
    adapter = _sim_adapter
    if not adapter or not adapter.is_connected:
        return "DISCONNECTED"
    if not adapter.is_armed:
        return "LANDED"
    mode = str(adapter.flight_mode or "").upper()
    if "LAND" in mode:
        return "LANDING"
    telem = getattr(adapter, "telemetry", None)
    altitude = getattr(telem, "relative_altitude_m", None)
    return "AIRBORNE" if isinstance(altitude, (int, float)) and altitude > 1.0 else "ARMED"


def _log_flight_command(command: str, status: str, detail: str = "") -> None:
    _flight_command_log.append({
        "timestamp": time.strftime("%H:%M:%S", time.localtime()),
        "command": command,
        "status": status,
        "detail": detail,
    })
    del _flight_command_log[:-100]


def _require_flight_state(command: str, allowed: Set[str]) -> None:
    state = _flight_state()
    if state not in allowed:
        _log_flight_command(command, "REJECTED", f"Vehicle state is {state}")
        raise HTTPException(status_code=409, detail=f"{command} is not allowed while vehicle is {state}.")


def _command_response(command: str, success: bool, detail: str = "", target_altitude: Optional[float] = None) -> Dict[str, Any]:
    adapter = _sim_adapter
    ack_value = getattr(adapter, "last_command_ack", None) if adapter else None
    ack = f"MAV_RESULT_{ack_value}" if ack_value is not None else None
    message = detail or (getattr(adapter, "last_command_message", "") if adapter else "")
    if not message:
        message = f"{command} command accepted by the adapter." if success else f"{command} command was rejected without an ACK."
    status = "ACCEPTED" if success else ("ACK_UNKNOWN" if ack_value is None else "REJECTED")
    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _log_flight_command(command, status, message)
    return {
        "command": command,
        "status": status,
        "ack": ack,
        "message": message,
        "timestamp": timestamp,
        "target_altitude": target_altitude,
        "success": success,
    }


# Simulator subsystem integration
# SIMULATOR_MODE: 'local' (ArduPilot/PX4 SITL via MAVLink TCP/UDP)
#                 'cloud' (Remote PX4/ArduPilot SITL container)
#                 'fallback' (Offline test fixture — CI/offline dev)
_sim_mode = os.getenv("SIMULATOR_MODE", "local").lower()
_sim_adapter: Optional[BaseSimulatorAdapter] = None
_telemetry_mgr: Optional[TelemetryManager] = None
_frame_mgr: FrameManager = FrameManager(max_fps=15)
_ws_clients: Set[WebSocket] = set()


async def _stop_telemetry_pipeline() -> None:
    global _telemetry_mgr
    if _telemetry_mgr is None:
        return
    try:
        await _telemetry_mgr.stop()
    except Exception:
        logger.exception("[Backend] Telemetry manager stop failed")
    finally:
        _telemetry_mgr = None


async def _close_sim_adapter(adapter: Optional[BaseSimulatorAdapter]) -> None:
    if adapter is None:
        return
    try:
        await adapter.disconnect()
    except Exception:
        logger.exception("[Backend] Adapter disconnect failed")


def _init_adapter(
    mode: str = "local",
    host: Optional[str] = None,
    port: Optional[int] = None,
    endpoint: Optional[str] = None
) -> BaseSimulatorAdapter:
    """
    Instantiate the appropriate simulator adapter.

    Modes:
      'local'    — ArduPilot/PX4 SITL running locally via MAVLink
                   Default endpoint: udp:172.30.16.1:14550 (real dev workstation path)
      'cloud'    — Remote PX4/ArduPilot SITL container via MAVLink over network
      'fallback' — In-memory offline test fixture (CI / development without simulator)
    """
    global _sim_adapter, _telemetry_mgr
    m = _normalize_runtime_mode(mode)
    if m == "local":
        # Real workstation path: MAVProxy relays ArduPilot SITL telemetry/commands to the host UDP port.
        conn = endpoint or os.getenv("MAVLINK_ENDPOINT", "udp:172.30.16.1:14550")
        logger.info(f"[Backend] Initialising LOCAL MAVLink adapter: {conn}")
        _sim_adapter = PX4Adapter(connection_string=conn)
    elif m == "cloud":
        conn = endpoint or os.getenv("MAVLINK_ENDPOINT", f"udpin:0.0.0.0:{port or 14550}")
        logger.info(f"[Backend] Initialising CLOUD MAVLink adapter: host={host} conn={conn}")
        _sim_adapter = CloudAdapter(host=host, port=port, mavlink_endpoint=conn)
    elif m == "fallback":
        # fallback — offline in-memory test fixture
        if m not in ("fallback",):
            logger.warning(f"[Backend] Unrecognised SIMULATOR_MODE '{mode}' — using FallbackAdapter (offline dev)")
        else:
            logger.info("[Backend] Initialising FALLBACK adapter (offline test fixture)")
        _sim_adapter = FallbackAdapter(mavlink_port=port or 14550)
    else:
        raise ValueError(f"Unsupported simulator mode: {mode}")

    if _telemetry_mgr:
        _telemetry_mgr.set_adapter(_sim_adapter)
    return _sim_adapter


def _attach_synthetic_camera() -> None:
    """Attach the synthetic world camera to the active simulator adapter."""
    if _sim_adapter is None or isinstance(_sim_adapter, FallbackAdapter):
        return

    provider = SyntheticCameraProvider(adapter=_sim_adapter)
    _sim_adapter.set_camera_provider(provider)
    _refresh_camera_state_from_adapter()

    logger.info("[Backend] Synthetic camera provider attached to simulator adapter")

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
    if _telemetry_store is None:
        _telemetry_store = TelemetryData()
    _runtime_state.update({
        "connected": bool(_sim_adapter and _sim_adapter.is_connected),
        "connection_state": "CONNECTED" if _sim_adapter and _sim_adapter.is_connected else "DISCONNECTED",
        "heartbeat_received": bool(_sim_adapter and _sim_adapter.is_connected),
        "system_id": getattr(_sim_adapter, "target_system", _runtime_state["system_id"]),
        "component_id": getattr(_sim_adapter, "target_component", _runtime_state["component_id"]),
        "autopilot": "ArduPilot" if getattr(_sim_adapter, "autopilot_type", 0) == 3 else "PX4" if getattr(_sim_adapter, "autopilot_type", 0) == 12 else _runtime_state["autopilot"],
        "vehicle": "ArduCopter" if getattr(_sim_adapter, "vehicle_type", None) == 2 else _runtime_state["vehicle"],
        "armed": bool(telem.get("isArmed", _runtime_state["armed"])),
        "mode": telem.get("flightMode", _runtime_state["mode"]),
        "latitude": telem.get("lat", _runtime_state["latitude"]),
        "longitude": telem.get("lng", _runtime_state["longitude"]),
        "altitude": telem.get("altitude", _runtime_state["altitude"]),
        "relative_altitude": telem.get("relativeAltitude", _runtime_state["relative_altitude"]),
        "ground_speed": telem.get("speed", _runtime_state["ground_speed"]),
        "heading": telem.get("headingDegrees", _runtime_state["heading"]),
        "roll": telem.get("roll", _runtime_state["roll"]),
        "pitch": telem.get("pitch", _runtime_state["pitch"]),
        "yaw": telem.get("yaw", _runtime_state["yaw"]),
        "battery": telem.get("battery", _runtime_state["battery"]),
        "gps_fix": telem.get("gpsStatus", _runtime_state["gps_fix"]),
        "satellites": telem.get("gpsSatellites", _runtime_state["satellites"]),
        "timestamp": telem.get("timestamp", _runtime_state["timestamp"]),
    })
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


def _get_visible_world_targets(telem: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Read visible synthetic targets from the active camera/world provider."""
    adapter = _sim_adapter
    if adapter is None:
        return []

    provider = getattr(adapter, "_camera_provider", None)
    if provider is not None and hasattr(provider, "get_visible_targets"):
        return provider.get_visible_targets(
            latitude=float(telem.get("lat") or 0.0),
            longitude=float(telem.get("lng") or 0.0),
            altitude_m=float(telem.get("relativeAltitude", telem.get("altitude")) or 0.0),
            heading_deg=float(telem.get("headingDegrees") or 0.0),
        )

    world = getattr(adapter, "world", None)
    if world is None and provider is not None:
        world = getattr(provider, "world", None)
    if world is None or not hasattr(world, "get_entities_in_camera_fov"):
        return []

    return world.get_entities_in_camera_fov(
        uav_lat=float(telem.get("lat") or 0.0),
        uav_lng=float(telem.get("lng") or 0.0),
        uav_alt_m=float(telem.get("relativeAltitude", telem.get("altitude")) or 0.0),
        uav_heading_deg=float(telem.get("headingDegrees") or 0.0),
    )


async def _on_perception_telemetry_update(telem: Dict[str, Any]):
    """Run the lightweight VirtualDetector from the existing telemetry lifecycle."""
    global _perception_last_inference, _perception_frame_id
    if _detector is None or _sim_adapter is None:
        return

    now = _perception_clock()
    if now - _perception_last_inference < _perception_inference_interval_s:
        return
    _perception_last_inference = now

    try:
        frame = await _sim_adapter.get_camera_frame()
        if frame is None:
            logger.warning("[Perception] No camera frame available; skipping cycle")
            return

        visible_targets = normalize_world_targets(_get_visible_world_targets(telem))
        _perception_frame_id += 1
        detections = _detector.detect(
            frame=frame,
            uav_lat=float(telem.get("lat") or 0.0),
            uav_lng=float(telem.get("lng") or 0.0),
            altitude_m=float(telem.get("relativeAltitude", telem.get("altitude")) or 0.0),
            timestamp=str(telem.get("timestamp") or time.strftime("%H:%M:%S UTC", time.gmtime())),
            visible_targets=visible_targets,
            frame_id=_perception_frame_id,
        )

        for detection_data in detections:
            request = DetectionRequest.model_validate(detection_data)
            process_detection_request(request, battery_percent_override=telem.get("battery"))
    except Exception:
        logger.exception("[Perception] Virtual detection cycle failed")


def _register_perception_listener() -> None:
    """Register the perception listener once for the active telemetry manager."""
    global _perception_listener_registered
    if _telemetry_mgr is None or _perception_listener_registered:
        return
    _telemetry_mgr.add_listener(_on_perception_telemetry_update)
    _perception_listener_registered = True
    logger.info("[Perception] perception listener registered")


def _unregister_perception_listener() -> None:
    """Remove the perception listener from the active telemetry manager."""
    global _perception_listener_registered
    if _telemetry_mgr is not None and _perception_listener_registered:
        _telemetry_mgr.remove_listener(_on_perception_telemetry_update)
    _perception_listener_registered = False


def _initialize_detector() -> None:
    """Initialize the configured detector and expose truthful readiness state."""
    global _detector, _detector_status
    configured = os.getenv("SIGHT_DETECTOR_BACKEND", "virtual").strip().lower()
    model_path = os.getenv("SIGHT_YOLO_MODEL_PATH", "yolo11n.pt")
    allow_fallback = os.getenv("SIGHT_ALLOW_DETECTOR_FALLBACK", "true").strip().lower() in {"1", "true", "yes"}
    _detector_status = {
        "configuredDetector": configured,
        "activeDetector": "none",
        "fallback": False,
        "reason": "",
        "modelPath": model_path if configured == "yolo" else None,
        "modelFound": None,
        "modelLoaded": False,
        "runtime": "UNKNOWN",
        "device": os.getenv("SIGHT_YOLO_DEVICE", "auto") if configured == "yolo" else None,
    }
    try:
        if configured == "virtual":
            _detector = VirtualDetector()
            _detector_status.update(activeDetector="virtual", runtime="READY", runtimeAvailable=True, inferenceReady=True, reason="Configured virtual detector")
            logger.info("[Perception] VirtualDetector initialized")
            return
        if configured != "yolo":
            _detector = None
            _detector_status.update(runtime="UNAVAILABLE", reason=f"Unsupported detector backend: {configured}")
            logger.error("[Perception] Unsupported detector backend: %s", configured)
            return

        detector = YOLODetector(
            model_path=model_path,
            device=_detector_status["device"],
            confidence_threshold=float(os.getenv("SIGHT_YOLO_CONFIDENCE", "0.25")),
            iou_threshold=float(os.getenv("SIGHT_TRACK_IOU_THRESHOLD", "0.3")),
            max_missed_frames=int(os.getenv("SIGHT_TRACK_MAX_MISSED_FRAMES", "3")),
        )
        _detector_status.update(
            activeDetector="yolo" if detector.is_available() else "none",
            modelFound=os.path.isfile(model_path),
            modelLoaded=detector.is_available(),
            runtimeAvailable=detector.load_error != "ultralytics is not installed",
            inferenceReady=detector.is_available(),
            runtime="READY" if detector.is_available() else "UNAVAILABLE",
            reason=detector.load_error or "YOLO detector ready",
        )
        if detector.is_available():
            _detector = detector
            logger.info("[Perception] YOLODetector initialized: model=%s", model_path)
        elif allow_fallback:
            _detector = VirtualDetector()
            _detector_status.update(activeDetector="virtual", fallback=True, reason=detector.load_error or "YOLO unavailable")
            logger.warning("[Perception] YOLO unavailable; using VirtualDetector fallback: %s", detector.load_error)
        else:
            _detector = None
            logger.error("[Perception] YOLO unavailable and fallback disabled: %s", detector.load_error)
    except Exception:
        _detector = None
        _detector_status.update(runtime="ERROR", reason="Detector initialization failed")
        logger.exception("[Perception] Detector initialization failed")


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

@app.get("/api/v1/health", tags=["System"])
@app.get("/health", tags=["System"])
def health():
    return {
        "status": "ok",
        "service": "sight-simulator-backend",
        "version": app.version,
        "components": {
            "governor": "online",
            "mission_card": "online",
            "communication_controller": "online",
            "detector": "not_connected",
        },
        "uptime_s": round(time.time() - _START_TIME, 3),
    }


@app.get("/api/v1/runtime/status", tags=["Runtime"])
def runtime_status():
    state = _refresh_runtime_state_from_adapter()
    state.update({
        "runtime": "ardupilot_sitl",
        "connected": state.get("connected", False),
        "system_id": state.get("system_id"),
        "component_id": state.get("component_id"),
        "autopilot": state.get("autopilot"),
        "vehicle": state.get("vehicle"),
        "armed": state.get("armed"),
        "mode": state.get("mode"),
        "latitude": state.get("latitude"),
        "longitude": state.get("longitude"),
        "altitude": state.get("altitude"),
        "relative_altitude": state.get("relative_altitude"),
        "ground_speed": state.get("ground_speed"),
        "heading": state.get("heading"),
        "roll": state.get("roll"),
        "pitch": state.get("pitch"),
        "yaw": state.get("yaw"),
        "battery": state.get("battery"),
        "gps_fix": state.get("gps_fix"),
        "satellites": state.get("satellites"),
        "timestamp": state.get("timestamp"),
    })
    return state


@app.post("/api/v1/runtime/connect", tags=["Runtime"])
async def runtime_connect(payload: Dict[str, Any] = Body(default={"connection": "udp:172.30.16.1:14550"})):
    global _sim_adapter, _telemetry_mgr
    connection = payload.get("connection") or "udp:172.30.16.1:14550"

    old_adapter = _sim_adapter
    if old_adapter is not None:
        await _close_sim_adapter(old_adapter)
    await _stop_telemetry_pipeline()

    _init_adapter(mode="local", endpoint=connection)
    connected = await _sim_adapter.connect() if _sim_adapter else False


    if connected:
        _attach_synthetic_camera()
    _refresh_camera_state_from_adapter()

    if _telemetry_mgr is None:
        _telemetry_mgr = TelemetryManager(adapter=_sim_adapter, rate_hz=10.0)
        _telemetry_mgr.add_listener(_on_telemetry_update)
        _register_perception_listener()
        await _telemetry_mgr.start()
    else:
        _telemetry_mgr.set_adapter(_sim_adapter)
        await _telemetry_mgr.start()

    _runtime_state.update({
        "connection_state": "CONNECTED" if connected else "DISCONNECTED",
        "heartbeat_received": bool(connected),
        "connected": bool(connected),
        "connection": connection,
        "system_id": getattr(_sim_adapter, "target_system", None) if connected else None,
        "component_id": getattr(_sim_adapter, "target_component", None) if connected else None,
        "autopilot": "ArduPilot" if connected and getattr(_sim_adapter, "autopilot_type", 0) == 3 else "PX4" if connected and getattr(_sim_adapter, "autopilot_type", 0) == 12 else None,
        "vehicle": "ArduCopter" if connected and getattr(_sim_adapter, "vehicle_type", None) == 2 else None,
    })
    _refresh_runtime_state_from_adapter()
    await _broadcast_ws(build_connection_event("connected" if connected else "disconnected", "ardupilot_sitl"))
    return {"connected": bool(connected), "connection": connection, "system_id": _runtime_state["system_id"], "component_id": _runtime_state["component_id"]}


@app.post("/api/v1/runtime/disconnect", tags=["Runtime"])
async def runtime_disconnect():
    global _sim_adapter, _telemetry_mgr
    await _stop_telemetry_pipeline()
    await _close_sim_adapter(_sim_adapter)
    _sim_adapter = None
    _runtime_state.update({
        "connected": False,
        "connection_state": "DISCONNECTED",
        "heartbeat_received": False,
        "system_id": None,
        "component_id": None,
        "autopilot": None,
        "vehicle": None,
        "armed": None,
        "mode": None,
        "latitude": None,
        "longitude": None,
        "altitude": None,
        "relative_altitude": None,
        "ground_speed": None,
        "heading": None,
        "roll": None,
        "pitch": None,
        "yaw": None,
        "battery": None,
        "gps_fix": None,
        "satellites": None,
        "timestamp": None,
    })
    await _broadcast_ws(build_connection_event("disconnected", "ardupilot_sitl"))
    return {"connected": False}


@app.post("/api/v1/vehicle/arm", tags=["Vehicle"])
async def vehicle_arm():
    if not _sim_adapter or not _sim_adapter.is_connected:
        raise HTTPException(status_code=400, detail="Simulator not connected")
    success = await _sim_adapter.arm()
    return {"requested": True, "accepted": success, "rejected": not success, "timeout": False, "actual_state": "armed" if success else "unchanged"}


@app.post("/api/v1/vehicle/disarm", tags=["Vehicle"])
async def vehicle_disarm():
    if not _sim_adapter or not _sim_adapter.is_connected:
        raise HTTPException(status_code=400, detail="Simulator not connected")
    success = await _sim_adapter.disarm()
    return {"requested": True, "accepted": success, "rejected": not success, "timeout": False, "actual_state": "disarmed" if success else "unchanged"}


@app.post("/api/v1/vehicle/takeoff", tags=["Vehicle"])
async def vehicle_takeoff(payload: Dict[str, Any] = Body(default={"altitude": 10})):
    if not _sim_adapter or not _sim_adapter.is_connected:
        raise HTTPException(status_code=400, detail="Simulator not connected")
    altitude = float(payload.get("altitude", 10.0))
    success = await _sim_adapter.takeoff(altitude)
    return {"requested": True, "accepted": success, "rejected": not success, "timeout": False, "actual_state": "takeoff" if success else "unchanged"}


@app.post("/api/v1/vehicle/land", tags=["Vehicle"])
async def vehicle_land():
    if not _sim_adapter or not _sim_adapter.is_connected:
        raise HTTPException(status_code=400, detail="Simulator not connected")
    success = await _sim_adapter.land()
    return {"requested": True, "accepted": success, "rejected": not success, "timeout": False, "actual_state": "land" if success else "unchanged"}


@app.post("/api/v1/vehicle/rtl", tags=["Vehicle"])
async def vehicle_rtl():
    if not _sim_adapter or not _sim_adapter.is_connected:
        raise HTTPException(status_code=400, detail="Simulator not connected")
    success = await _sim_adapter.return_to_home()
    return {"requested": True, "accepted": success, "rejected": not success, "timeout": False, "actual_state": "rtl" if success else "unchanged"}


@app.post("/api/v1/vehicle/emergency-stop", tags=["Vehicle"])
async def vehicle_emergency_stop():
    if not _sim_adapter or not _sim_adapter.is_connected:
        raise HTTPException(status_code=400, detail="Simulator not connected")
    success = await _sim_adapter.disarm()
    return {"requested": True, "accepted": success, "rejected": not success, "timeout": False, "actual_state": "emergency_stop" if success else "unchanged"}


@app.get("/api/v1/parameters", tags=["Parameters"]) 
def get_parameters():
    return list_parameters()


@app.get("/api/v1/parameters/{name}", tags=["Parameters"]) 
def get_parameter_value(name: str):
    return get_parameter(name.upper())


@app.post("/api/v1/parameters/{name}", tags=["Parameters"]) 
def post_parameter_value(name: str, payload: Dict[str, Any] = Body(default={"value": 0})):
    value = payload.get("value")
    return set_parameter(name.upper(), value)


@app.get("/api/v1/mission", tags=["Mission"])
def get_mission_runtime():
    card = _mission_manager.active_card
    if not card:
        raise HTTPException(status_code=404, detail="No active mission card")
    return card.model_dump(by_alias=True)


@app.post("/api/v1/mission", tags=["Mission"])
def post_mission_runtime(payload: Dict[str, Any] = Body(default={"missionId": "SIGHT-M01"})):
    mission_payload = dict(payload)
    if "missionId" not in mission_payload and "mission_id" in mission_payload:
        mission_payload["missionId"] = mission_payload["mission_id"]
    if "relevantObjects" not in mission_payload and "relevant_objects" in mission_payload:
        mission_payload["relevantObjects"] = mission_payload["relevant_objects"]
    if "persistenceFrames" not in mission_payload and "persistence_frames" in mission_payload:
        mission_payload["persistenceFrames"] = mission_payload["persistence_frames"]
    if "batteryRthPercent" not in mission_payload and "battery_rth_percent" in mission_payload:
        mission_payload["batteryRthPercent"] = mission_payload["battery_rth_percent"]
    if "minConfidencePercent" not in mission_payload and "min_confidence_percent" in mission_payload:
        mission_payload["minConfidencePercent"] = mission_payload["min_confidence_percent"]
    if "communicationPolicy" not in mission_payload and "communication_policy" in mission_payload:
        mission_payload["communicationPolicy"] = mission_payload["communication_policy"]

    try:
        req = MissionCardRequest.model_validate(mission_payload)
        card_dict = req.model_dump(by_alias=True)
        _mission_manager.load_from_dict(card_dict)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    card = _mission_manager.active_card
    return MissionCardResponse(
        status="OK",
        mission_id=card.mission_id,
        message=f"Mission card '{card.mission_id}' loaded successfully.",
    )


@app.put("/api/v1/mission", tags=["Mission"])
def put_mission_runtime(payload: Dict[str, Any] = Body(default={"missionId": "SIGHT-M01"})):
    return post_mission_runtime(payload)


@app.post("/api/v1/mission/load", tags=["Mission"])
def mission_load(payload: Dict[str, Any] = Body(default={"missionId": "SIGHT-M01"})):
    return post_mission_runtime(payload)


@app.get("/api/v1/sight/governor/status", tags=["Governor"]) 
def governor_status_runtime():
    last_decision = _latest_governor_state or {"decision": "RETAIN", "reason": "No detection yet", "action": "None", "mission_id": "SIGHT-M01", "target_type": None, "zone_name": None, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "evaluated_conditions": {"communicationAvailable": True, "batteryAboveThreshold": True, "relevantObject": True, "insidePriorityZone": True, "persistenceSatisfied": True, "evidenceRequired": False}}
    return last_decision


@app.get("/api/v1/communication/status", tags=["Communication"]) 
def communication_status_runtime():
    return {"state": "ACTIVE", "packets_generated": 0, "packets_suppressed": 0, "packets_retained": 0, "packets_transmitted": 0, "bytes_generated": 0, "bytes_transmitted": 0, "events": 0, "evidence": 0, "outage": False}


@app.post("/api/v1/communication/configure", tags=["Communication"]) 
def communication_configure(payload: Dict[str, Any] = Body(default={"bandwidth": 256, "latency": 80, "jitter": 20, "packet_loss": 5, "outage": False})):
    return {"status": "ok", "config": payload}


@app.get("/api/v1/world/entities", tags=["World"]) 
def world_entities():
    return {"entities": _world_entities}


@app.post("/api/v1/world/entities", tags=["World"]) 
def create_world_entity(payload: Dict[str, Any] = Body(default={"id": "person-003", "type": "person"})):
    _world_entities.append(payload)
    return {"status": "ok", "entity": payload}


@app.delete("/api/v1/world/entities/{entity_id}", tags=["World"]) 
def delete_world_entity(entity_id: str):
    _world_entities[:] = [entity for entity in _world_entities if entity.get("id") != entity_id]
    return {"status": "deleted", "id": entity_id}


@app.get("/api/v1/failures", tags=["Failures"]) 
def get_failures():
    return {"failures": _failure_state}


@app.post("/api/v1/failures/apply", tags=["Failures"]) 
def apply_failure(payload: Dict[str, Any] = Body(default={"name": "gps_loss"})):
    name = payload.get("name")
    if name in _failure_state:
        _failure_state[name] = True
    return {"status": "applied", "name": name}


@app.post("/api/v1/failures/reset", tags=["Failures"]) 
def reset_failures():
    for key in _failure_state:
        _failure_state[key] = False
    return {"status": "reset", "failures": _failure_state}


@app.get("/api/v1/camera/status", tags=["Camera"]) 
def camera_status():
    return _refresh_camera_state_from_adapter()


@app.post("/api/v1/camera/start", tags=["Camera"]) 
def camera_start():
    _refresh_camera_state_from_adapter()
    return {"status": "CONNECTED" if _camera_state["online"] else "NOT CONNECTED", "camera": dict(_camera_state)}


@app.post("/api/v1/camera/stop", tags=["Camera"]) 
def camera_stop():
    global _camera_state
    _camera_state = {"status": "NOT CONNECTED", "online": False, "fps": None, "fov": None, "resolution": None}
    return {"status": "stopped", "camera": dict(_camera_state)}


# ─────────────────────────────────────────────
#  Telemetry
# ─────────────────────────────────────────────

@app.get("/api/v1/telemetry", response_model=TelemetryData, tags=["Telemetry"])
def get_telemetry():
    return _telemetry_store or TelemetryData()


@app.post("/api/v1/telemetry", tags=["Telemetry"])
def post_telemetry(data: TelemetryData):
    global _telemetry_store
    _telemetry_store = data
    return {"status": "OK"}


# ─────────────────────────────────────────────
#  Mission Card
# ─────────────────────────────────────────────

# ─────────────────────────────────────────────
#  Detection → Governor Pipeline
# ─────────────────────────────────────────────

def process_detection_request(
    req: DetectionRequest,
    battery_percent_override: Optional[float] = None,
) -> DetectionResponse:
    """Process one detection through Governor and CommunicationController."""
    global _latest_governor_state

    if not _mission_manager.active_card:
        raise HTTPException(status_code=400, detail="No active mission card. POST /api/v1/mission first.")
    stored_battery = _telemetry_store.battery_percent if _telemetry_store else None
    battery_percent = battery_percent_override if battery_percent_override is not None else stored_battery
    if battery_percent is None:
        raise HTTPException(status_code=409, detail="No genuine MAVLink telemetry received yet.")

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
        uav_battery_percent=battery_percent,
        communication_available=_comm_controller.link_available,
    )

    # Communication Controller dispatch
    det_dict = req.model_dump(by_alias=True)
    det_dict["zoneName"] = decision.zone_name
    det_dict["governorDecision"] = decision.decision
    det_dict["governorReason"] = decision.reason
    det_dict["insidePriorityZone"] = decision.evaluated_conditions.inside_priority_zone
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


@app.post("/api/v1/detect", response_model=DetectionResponse, tags=["Detection"])
def detect(req: DetectionRequest):
    """Submit one detection through the shared internal processing path."""
    return process_detection_request(req)


@app.post("/api/v1/detect", tags=["Detection"])
def detect_legacy(req: Dict[str, Any] = Body(default={})):  # compatibility shim for older tests
    """Accept legacy alias payloads and map them to the canonical DetectionRequest shape."""
    payload = dict(req)
    if "objectClass" not in payload and "object_class" in payload:
        payload["objectClass"] = payload["object_class"]
    if "normBbox" not in payload and "norm_bbox" in payload:
        payload["normBbox"] = payload["norm_bbox"]
    if "trackId" not in payload and "track_id" in payload:
        payload["trackId"] = payload["track_id"]
    if "altitudeM" not in payload and "altitude_m" in payload:
        payload["altitudeM"] = payload["altitude_m"]
    if "frameId" not in payload and "frame_id" in payload:
        payload["frameId"] = payload["frame_id"]

    model = DetectionRequest.model_validate(payload)
    return detect(model)


@app.get("/api/v1/detections", tags=["Detection"])
def get_detections(limit: int = 50):
    return _detection_log[-limit:]


@app.get("/api/v1/detector/status", tags=["Detection"])
def detector_status():
    status = dict(_detector_status)
    status.update({
        "configured": status.get("configuredDetector"),
        "active": status.get("activeDetector"),
        "runtime_available": status.get("runtimeAvailable"),
        "model_found": status.get("modelFound"),
        "model_loaded": status.get("modelLoaded"),
        "inference_ready": status.get("inferenceReady"),
        "active_detector": status.get("activeDetector"),
    })
    status["lastFrameId"] = _perception_frame_id
    status["detections"] = len(_detection_log)
    detector = _detector
    if isinstance(detector, YOLODetector):
        status["inferenceMs"] = detector.last_inference_ms
        status["inferenceCount"] = detector.inference_count
        status["lastSuccessfulInference"] = detector.last_successful_inference
        status["activeTracks"] = len(detector.tracker.active_tracks)
        status["expiredTracks"] = detector.tracker.expired_count
        status["maxMissedFrames"] = detector.tracker.max_missed_frames
    else:
        status["inferenceMs"] = None
        status["inferenceCount"] = 0
        status["lastSuccessfulInference"] = None
        status["activeTracks"] = 0
        status["expiredTracks"] = 0
        status["maxMissedFrames"] = None
    return status


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
    global _sim_adapter, _telemetry_mgr, _perception_frame_id
    _perception_frame_id = 0
    _initialize_detector()
    sim_mode = os.getenv("SIMULATOR_MODE", "local").lower()
    _init_adapter(mode=sim_mode)
    if _sim_adapter:
        try:
            connected = await _sim_adapter.connect()
            if connected:
                _attach_synthetic_camera()
                logger.info(f"[+] Simulator adapter connected: {_sim_adapter.mode_name.upper()}")
            else:
                logger.warning("[+] Simulator adapter not yet connected — waiting for MAVLink heartbeat.")
        except Exception as e:
            logger.warning(f"[+] Simulator connect deferred (SITL host not yet running): {e}")
    _refresh_camera_state_from_adapter()

    _telemetry_mgr = TelemetryManager(adapter=_sim_adapter, rate_hz=10.0)
    _telemetry_mgr.add_listener(_on_telemetry_update)
    _register_perception_listener()
    await _telemetry_mgr.start()
    logger.info("[+] S.I.G.H.T. Backend Startup Complete. Telemetry pipeline active.")


@app.on_event("shutdown")
async def shutdown_event():
    global _telemetry_mgr, _sim_adapter
    _unregister_perception_listener()
    await _stop_telemetry_pipeline()
    await _close_sim_adapter(_sim_adapter)
    _sim_adapter = None
    logger.info("[+] S.I.G.H.T. Backend Shutdown Complete.")


# ─────────────────────────────────────────────
#  WebSocket Telemetry & Decision Stream
# ─────────────────────────────────────────────

@app.websocket("/ws")
@app.websocket("/ws/telemetry")
@app.websocket("/ws/mission")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    _ws_clients.add(websocket)
    try:
        # Initial greeting with current system state
        telem_payload = _telemetry_store.model_dump() if _telemetry_store else {}
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
            status="OFFLINE", mode="none", is_connected=False, is_armed=None,
            flight_mode=None, link_status="LOST", battery_percent=None,
            altitude_m=None, lat=None, lng=None, message="No simulator adapter"
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


@app.get("/api/v1/flight/commands", tags=["Flight Control"])
def flight_commands():
    return {"state": _flight_state(), "entries": list(_flight_command_log)}


@app.post("/api/v1/flight/connect", tags=["Flight Control"])
async def flight_connect(req: ConnectSimulatorRequest):
    global _sim_adapter
    mode = _normalize_runtime_mode(req.mode)
    _init_adapter(mode=mode, host=req.host, port=req.port, endpoint=req.endpoint or os.getenv("MAVLINK_ENDPOINT", "udp:172.30.16.1:14550"))
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
    if not _sim_adapter or not _sim_adapter.is_connected:
        raise HTTPException(status_code=400, detail="Simulator not connected")
    _require_flight_state("ARM", {"LANDED", "ARMED"})
    success = await _sim_adapter.arm()
    return _command_response("ARM", success)


@app.post("/api/v1/flight/disarm", tags=["Flight Control"])
async def flight_disarm():
    if not _sim_adapter or not _sim_adapter.is_connected:
        raise HTTPException(status_code=400, detail="Simulator not connected")
    success = await _sim_adapter.disarm()
    return _command_response("DISARM", success)


@app.post("/api/v1/flight/takeoff", tags=["Flight Control"])
async def flight_takeoff(req: TakeoffRequest):
    if not _sim_adapter or not _sim_adapter.is_connected:
        raise HTTPException(status_code=400, detail="Simulator not connected")
    _require_flight_state("TAKEOFF", {"ARMED", "AIRBORNE"})
    success = await _sim_adapter.takeoff(altitude=req.altitude)
    return _command_response("TAKEOFF", success, target_altitude=req.altitude)


@app.post("/api/v1/flight/land", tags=["Flight Control"])
async def flight_land():
    if not _sim_adapter or not _sim_adapter.is_connected:
        raise HTTPException(status_code=400, detail="Simulator not connected")
    _require_flight_state("LAND", {"ARMED", "AIRBORNE", "LANDING"})
    success = await _sim_adapter.land()
    return _command_response("LAND", success)


@app.post("/api/v1/flight/hover", tags=["Flight Control"])
async def flight_hover():
    if not _sim_adapter or not _sim_adapter.is_connected:
        raise HTTPException(status_code=400, detail="Simulator not connected")
    _require_flight_state("HOVER", {"ARMED", "AIRBORNE"})
    success = await _sim_adapter.hover()
    return _command_response("LOITER", success)


@app.post("/api/v1/flight/move", tags=["Flight Control"])
async def flight_move(req: MoveRequest):
    if not _sim_adapter:
        raise HTTPException(status_code=400, detail="Simulator not connected")
    success = await _sim_adapter.move(vx=req.vx, vy=req.vy, vz=req.vz, yaw_rate=req.yaw_rate)
    return {"status": "MOVE_COMMANDED", "success": success}


@app.post("/api/v1/flight/heading", tags=["Flight Control"])
async def flight_heading(req: HeadingRequest):
    if not _sim_adapter or not _sim_adapter.is_connected:
        raise HTTPException(status_code=400, detail="Simulator not connected")
    _require_flight_state("HEADING", {"ARMED", "AIRBORNE"})
    success = await _sim_adapter.set_heading(heading_deg=req.heading)
    return _command_response("HEADING", success, detail=f"Heading command {'accepted' if success else 'rejected'} for {req.heading:g} degrees.")


@app.post("/api/v1/flight/rth", tags=["Flight Control"])
async def flight_rth():
    if not _sim_adapter or not _sim_adapter.is_connected:
        raise HTTPException(status_code=400, detail="Simulator not connected")
    _require_flight_state("RTL", {"ARMED", "AIRBORNE", "LANDING"})
    success = await _sim_adapter.return_to_home()
    return _command_response("RTL", success)


@app.post("/api/v1/mission/upload", tags=["Mission"])
async def mission_upload():
    if not _sim_adapter or not _sim_adapter.is_connected:
        _log_flight_command("MISSION UPLOAD", "REJECTED", "SITL disconnected")
        return JSONResponse(status_code=409, content={
            "command": "MISSION UPLOAD", "status": "REJECTED", "success": False,
            "message": "SITL disconnected", "waypoints": 0,
        })

    card = _mission_manager.active_card
    waypoints = card.waypoints if card else []
    if not waypoints:
        _log_flight_command("MISSION UPLOAD", "REJECTED", "No waypoints defined")
        return JSONResponse(status_code=422, content={
            "command": "MISSION UPLOAD", "status": "REJECTED", "success": False,
            "message": "No waypoints defined", "waypoints": 0,
        })

    mission_waypoints = [waypoint.model_dump(by_alias=True) for waypoint in waypoints]
    valid = all(-90 <= item["lat"] <= 90 and -180 <= item["lon"] <= 180 and item["altitude"] >= 0 for item in mission_waypoints)
    if not valid:
        _log_flight_command("MISSION UPLOAD", "REJECTED", "Mission contains invalid waypoint coordinates or altitude")
        return JSONResponse(status_code=422, content={
            "command": "MISSION UPLOAD", "status": "REJECTED", "success": False,
            "message": "Mission contains invalid waypoint coordinates or altitude", "waypoints": len(waypoints),
        })

    success = await _sim_adapter.send_mission({"waypoints": mission_waypoints})
    ack_value = getattr(_sim_adapter, "last_mission_ack", None)
    ack = f"MAV_MISSION_RESULT_{ack_value}" if ack_value is not None else None
    status = "ACCEPTED" if success else ("REJECTED" if ack else "ACK_UNKNOWN")
    message = "Mission acknowledged by UAV." if success else (f"Mission rejected by UAV ({ack})." if ack else "No MISSION_ACK received before timeout.")
    _log_flight_command("MISSION UPLOAD", status, message)
    return {
        "command": "MISSION UPLOAD", "status": status, "success": success,
        "ack": ack, "message": message, "waypoints": len(waypoints),
    }


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





