"""
PROJECT S.I.G.H.T. Core - Mission Card Models
Defines structured schemas and validators for Mission Cards, priority zones,
and operational communication policies.
"""

from typing import List, Optional, Tuple, Literal
from pydantic import BaseModel, Field, field_validator

CommunicationPolicyType = Literal["EVENT ONLY", "EVENT & EVIDENCE", "SILENT", "ADAPTIVE"]
EvidencePolicyType = Literal["Enabled", "Disabled", "On-Demand"]
PriorityType = Literal["HIGH", "MEDIUM", "LOW"]

class Waypoint(BaseModel):
    id: str
    name: str = "Waypoint"
    lat: float
    lon: float
    altitude: float = 20.0
    acceptance_radius: float = Field(default=10.0, alias="acceptanceRadius")

    model_config = {"populate_by_name": True}

    @field_validator("lat")
    @classmethod
    def validate_latitude(cls, v: float) -> float:
        if not -90.0 <= v <= 90.0:
            raise ValueError("Waypoint latitude must be between -90 and 90 degrees.")
        return v

    @field_validator("lon")
    @classmethod
    def validate_longitude(cls, v: float) -> float:
        if not -180.0 <= v <= 180.0:
            raise ValueError("Waypoint longitude must be between -180 and 180 degrees.")
        return v

    @field_validator("altitude", "acceptance_radius")
    @classmethod
    def validate_positive_measurement(cls, v: float) -> float:
        if v < 0:
            raise ValueError("Waypoint altitude and acceptance radius must not be negative.")
        return v

class PriorityZone(BaseModel):
    id: str
    name: str
    polygon: List[Tuple[float, float]] # [(lat, lng), ...]
    description: Optional[str] = ""
    priority: PriorityType = "HIGH"
    active: bool = True

    @field_validator("polygon")
    @classmethod
    def validate_polygon(cls, v: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        if len(v) < 3:
            raise ValueError("Priority zone polygon must have at least 3 coordinate vertices.")
        for pt in v:
            if not (-90.0 <= pt[0] <= 90.0) or not (-180.0 <= pt[1] <= 180.0):
                raise ValueError(f"Invalid coordinate in polygon: {pt}")
        return v

class MissionCard(BaseModel):
    mission_id: str = Field(..., alias="missionId")
    objective: str
    uav_id: str = Field(default="SIGHT-UAV-01", alias="uavId")
    relevant_objects: List[str] = Field(default=["Person", "Vehicle"], alias="relevantObjects")
    persistence: str = "2 frames"
    persistence_frames: int = Field(default=2, alias="persistenceFrames")
    waypoints: List[Waypoint] = Field(default_factory=list)
    priority_zones: List[PriorityZone] = Field(default_factory=list, alias="priorityZones")
    evidence: EvidencePolicyType = "Disabled"
    communication_policy: CommunicationPolicyType = Field(default="EVENT ONLY", alias="communicationPolicy")
    battery_rth_threshold: str = Field(default="20%", alias="batteryRthThreshold")
    battery_rth_percent: float = Field(default=20.0, alias="batteryRthPercent")
    min_confidence_percent: float = Field(default=60.0, alias="minConfidencePercent")
    description: Optional[str] = ""

    model_config = {
        "populate_by_name": True,
        "arbitrary_types_allowed": True
    }

    @field_validator("battery_rth_percent")
    @classmethod
    def validate_rth(cls, v: float) -> float:
        if not (5.0 <= v <= 50.0):
            raise ValueError("Battery RTH threshold must be between 5% and 50%.")
        return v

    @field_validator("persistence_frames")
    @classmethod
    def validate_persistence(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Persistence frame threshold must be at least 1 frame.")
        return v
