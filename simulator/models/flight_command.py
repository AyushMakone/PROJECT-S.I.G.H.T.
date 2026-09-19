"""
PROJECT S.I.G.H.T. — Flight Command Models & Results
Validates and standardizes commands dispatched to the drone simulator.
"""

from typing import Optional, Literal
from pydantic import BaseModel, Field


CommandType = Literal[
    "CONNECT",
    "DISCONNECT",
    "ARM",
    "DISARM",
    "TAKEOFF",
    "LAND",
    "HOVER",
    "MOVE",
    "ROTATE",
    "YAW",
    "RTH",
    "EMERGENCY_STOP"
]

CommandStatus = Literal[
    "accepted",
    "rejected",
    "unsupported",
    "failed"
]


class FlightCommandRequest(BaseModel):
    command: CommandType
    altitude: Optional[float] = Field(default=None, description="Target altitude for takeoff in meters")
    vx: Optional[float] = Field(default=0.0, description="Velocity along X (forward/back) m/s")
    vy: Optional[float] = Field(default=0.0, description="Velocity along Y (right/left) m/s")
    vz: Optional[float] = Field(default=0.0, description="Velocity along Z (up/down) m/s")
    yaw_rate: Optional[float] = Field(default=0.0, description="Angular yaw rate in deg/s")
    heading_deg: Optional[float] = Field(default=None, description="Target heading angle in degrees (0-360)")


class FlightCommandResult(BaseModel):
    command: str
    status: CommandStatus
    message: Optional[str] = None
    success: bool = False
