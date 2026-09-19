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
    lat: float = 28.7041
    lng: float = 77.1025
    altitude_m: float = 0.0
    speed_mps: float = 0.0
    heading_deg: float = 0.0
    climb_rate_mps: float = 0.0
    roll_deg: float = 0.0
    pitch_deg: float = 0.0
    yaw_deg: float = 0.0
    battery_percent: float = 100.0
    battery_voltage_v: float = 16.8
    is_armed: bool = False
    flight_mode: str = "STABILIZED"
    current_waypoint: int = 0
    total_waypoints: int = 0
    timestamp_utc: str = ""


# ─────────────────────────────────────────────
#  Mission Card Schema
# ─────────────────────────────────────────────

class PriorityZoneRequest(BaseModel):
    id: str
    name: str
    polygon: List[Tuple[float, float]]
    description: Optional[str] = ""

    model_config = {"populate_by_name": True}


class MissionCardRequest(BaseModel):
    mission_id: str = Field(..., alias="missionId")
    objective: str
    uav_id: str = Field(default="SIGHT-UAV-01", alias="uavId")
    relevant_objects: List[str] = Field(default=["Person", "Vehicle"], alias="relevantObjects")
    persistence_frames: int = Field(default=2, alias="persistenceFrames")
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
    mode: str = Field(default="online", description="'online' (LOS-Flight-Simulator), 'cloud', 'local', or 'fallback'")
    host: Optional[str] = None
    port: Optional[int] = None
    endpoint: Optional[str] = None
    simulator_url: Optional[str] = Field(default=None, description="Online Simulator Host URL (for mode='online')")
    ws_url: Optional[str] = Field(default=None, description="Online Simulator WebSocket URL (for mode='online')")



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
    is_armed: bool
    flight_mode: str
    link_status: str
    battery_percent: float
    altitude_m: float
    lat: float
    lng: float
    message: Optional[str] = None

