"""
PROJECT S.I.G.H.T. Backend — Pydantic Request/Response Schemas
Shared schemas used across FastAPI endpoints.
"""

from typing import Optional, Literal, List, Dict, Any, Tuple
from pydantic import BaseModel, Field
import time


# ─────────────────────────────────────────────
#  Detection Schema (Edge AI → Backend)
# ─────────────────────────────────────────────

class DetectionRequest(BaseModel):
    """Incoming detection from the Edge AI perception layer."""
    id: str = Field(..., description="Unique detection ID")
    object_class: str = Field(..., alias="objectClass", description="Detected class label")
    confidence: float = Field(..., ge=0.0, le=100.0, description="Detection confidence (0–100%)")
    norm_bbox: Tuple[float, float, float, float] = Field(
        ..., alias="normBbox",
        description="Normalized bbox (x, y, w, h) in [0,1]"
    )
    track_id: int = Field(default=1, alias="trackId")
    persistence: int = Field(default=1, ge=1)
    lat: float = Field(..., description="Target estimated latitude")
    lng: float = Field(..., description="Target estimated longitude")
    altitude_m: float = Field(default=0.0, alias="altitudeM")
    timestamp: str = Field(default_factory=lambda: time.strftime("%H:%M:%S UTC", time.gmtime()))
    frame_id: int = Field(default=0, alias="frameId")
    source: str = Field(default="VIRTUAL_DETECTOR", description="Detector backend identifier")
    location_source: str = Field(default="UAV_POSITION", alias="locationSource")
    target_geolocation_available: bool = Field(default=False, alias="targetGeolocationAvailable")

    model_config = {"populate_by_name": True}


class DetectionResponse(BaseModel):
    """Governor decision for a single detection."""
    detection_id: str
    object_class: str
    confidence: float
    decision: Literal["SUPPRESS", "RETAIN", "EVENT", "EVIDENCE"]
    reason: str
    action: str
    mission_id: str
    zone_name: Optional[str]
    timestamp: str
    evaluated_conditions: Dict[str, bool]


# ─────────────────────────────────────────────
#  Telemetry Schema
# ─────────────────────────────────────────────

class TelemetryData(BaseModel):
    lat: Optional[float] = None
    lng: Optional[float] = None
    altitude_m: Optional[float] = None
    speed_mps: Optional[float] = None
    heading_deg: Optional[float] = None
    climb_rate_mps: Optional[float] = None
    roll_deg: Optional[float] = None
    pitch_deg: Optional[float] = None
    yaw_deg: Optional[float] = None
    battery_percent: Optional[float] = None
    battery_voltage_v: Optional[float] = None
    is_armed: Optional[bool] = None
    flight_mode: Optional[str] = None
    current_waypoint: Optional[int] = None
    total_waypoints: Optional[int] = None
    timestamp_utc: Optional[str] = None


# ─────────────────────────────────────────────
#  Mission Card Schema
# ─────────────────────────────────────────────

class PriorityZoneRequest(BaseModel):
    id: str
    name: str
    polygon: List[Tuple[float, float]]
    description: Optional[str] = ""
    priority: Literal["HIGH", "MEDIUM", "LOW"] = "HIGH"
    active: bool = True

    model_config = {"populate_by_name": True}


class MissionCardRequest(BaseModel):
    mission_id: str = Field(..., alias="missionId")
    objective: str
    uav_id: str = Field(default="SIGHT-UAV-01", alias="uavId")
    relevant_objects: List[str] = Field(default=["Person", "Vehicle"], alias="relevantObjects")
    persistence_frames: int = Field(default=2, alias="persistenceFrames")
    waypoints: List[Dict[str, Any]] = Field(default_factory=list)
    priority_zones: List[PriorityZoneRequest] = Field(default_factory=list, alias="priorityZones")
    evidence: Literal["Enabled", "Disabled", "On-Demand"] = "Disabled"
    communication_policy: str = Field(default="EVENT ONLY", alias="communicationPolicy")
    battery_rth_percent: float = Field(default=20.0, alias="batteryRthPercent")
    min_confidence_percent: float = Field(default=60.0, alias="minConfidencePercent")
    description: Optional[str] = ""

    model_config = {"populate_by_name": True}


class MissionCardResponse(BaseModel):
    status: str
    mission_id: str
    message: str


# ─────────────────────────────────────────────
#  Governor State Schema
# ─────────────────────────────────────────────

class GovernorStateResponse(BaseModel):
    decision: Literal["SUPPRESS", "RETAIN", "EVENT", "EVIDENCE"]
    reason: str
    action: str
    mission_id: str
    target_type: Optional[str]
    zone_name: Optional[str]
    timestamp: str
    evaluated_conditions: Dict[str, bool]


# ─────────────────────────────────────────────
#  Communication Status Schema
# ─────────────────────────────────────────────

class CommStateResponse(BaseModel):
    state: Literal["INACTIVE", "ACTIVATE", "TRANSMIT", "VERIFY"]
    packets_sent: int
    bytes_transmitted: int
    events_transmitted: int
    evidence_transmitted: int
    suppressed: int
    retained: int
    last_transmission_ms: Optional[float]
    link_available: bool


# ─────────────────────────────────────────────
#  Health Schema
# ─────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str
    components: Dict[str, str]
    uptime_s: float


# ─────────────────────────────────────────────
#  Flight Control & Simulator Schemas
# ─────────────────────────────────────────────

class ConnectSimulatorRequest(BaseModel):
    mode: str = Field(default="local", description="'local' (real ArduPilot SITL via MAVProxy), 'cloud', or 'fallback'")
    host: Optional[str] = None
    port: Optional[int] = None
    endpoint: Optional[str] = None
    simulator_url: Optional[str] = Field(default=None, description="Remote simulator host URL")
    ws_url: Optional[str] = Field(default=None, description="Remote simulator websocket URL")



class TakeoffRequest(BaseModel):
    altitude: float = Field(default=10.0, ge=1.0, le=500.0, description="Takeoff altitude in meters")


class MoveRequest(BaseModel):
    vx: float = Field(default=0.0, description="Forward velocity (m/s)")
    vy: float = Field(default=0.0, description="Right velocity (m/s)")
    vz: float = Field(default=0.0, description="Down velocity (m/s, negative for climb)")
    yaw_rate: float = Field(default=0.0, description="Yaw turn rate (deg/s)")


class HeadingRequest(BaseModel):
    heading: float = Field(..., ge=0.0, le=360.0, description="Target compass heading in degrees")


class FlightStatusResponse(BaseModel):
    status: str
    mode: str
    is_connected: bool
    is_armed: Optional[bool]
    flight_mode: Optional[str]
    link_status: str
    battery_percent: Optional[float]
    altitude_m: Optional[float]
    lat: Optional[float]
    lng: Optional[float]
    message: Optional[str] = None


class FlightCommandResponse(BaseModel):
    command: str
    status: Literal["ACCEPTED", "REJECTED", "FAILED", "ACK_UNKNOWN"]
    ack: Optional[str] = None
    message: str
    timestamp: str
    target_altitude: Optional[float] = None

