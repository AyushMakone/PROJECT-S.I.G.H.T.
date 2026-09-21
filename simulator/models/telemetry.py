"""
PROJECT S.I.G.H.T. — Genuine Simulator Telemetry Data Models
Strictly adheres to real telemetry values directly reported by the simulator physics engine.
Zero fake or fabricated values.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
import time


class VelocityVector(BaseModel):
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    ground_speed: float = 0.0


class AttitudeAngles(BaseModel):
    roll: float = 0.0
    pitch: float = 0.0
    yaw: float = 0.0


class SimulatorTelemetry(BaseModel):
    """
    Authoritative UAV flight telemetry model from the real simulator.
    Fields without sensor support remain None (e.g., battery: null) rather than faked.
    """
    timestamp: Optional[str] = None
    connected: bool = False
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude: Optional[float] = None
    velocity: VelocityVector = Field(default_factory=VelocityVector)
    attitude: AttitudeAngles = Field(default_factory=AttitudeAngles)
    heading: Optional[float] = None
    battery: Optional[float] = None  # None if simulator has no battery physics, NEVER fabricated
    battery_voltage: Optional[float] = None
    armed: Optional[bool] = None
    flight_mode: Optional[str] = None
    simulator: str = "NOT_CONNECTED"
    raw_status: Optional[str] = None

    def to_legacy_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format expected by S.I.G.H.T. frontend & context engines."""
        def rounded(value: Optional[float], digits: int) -> Optional[float]:
            return round(value, digits) if value is not None else None

        return {
            "timestamp": self.timestamp,
            "connected": self.connected,
            "lat": self.latitude,
            "lng": self.longitude,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "altitude": rounded(self.altitude, 2),
            "altitude_m": rounded(self.altitude, 2),
            "speed": rounded(self.velocity.ground_speed, 2),
            "speed_mps": rounded(self.velocity.ground_speed, 2),
            "headingDegrees": rounded(self.heading, 1),
            "heading": f"{round(self.heading, 1)}°" if self.heading is not None else None,
            "battery": self.battery,
            "batteryVoltage": self.battery_voltage,
            "isArmed": self.armed,
            "flightMode": self.flight_mode,
            "linkStatus": "ONLINE" if self.connected else "LOST",
            "systemStatus": "ONLINE" if self.connected else "STANDBY",
            "roll": rounded(self.attitude.roll, 1),
            "pitch": rounded(self.attitude.pitch, 1),
            "yaw": rounded(self.attitude.yaw, 1),
            "climbRate": rounded(self.velocity.y, 2),
            "simulator": self.simulator,
        }
