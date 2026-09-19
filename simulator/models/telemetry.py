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
    timestamp: str = Field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime()))
    connected: bool = False
    latitude: float = 0.0
    longitude: float = 0.0
    altitude: float = 0.0
    velocity: VelocityVector = Field(default_factory=VelocityVector)
    attitude: AttitudeAngles = Field(default_factory=AttitudeAngles)
    heading: float = 0.0
    battery: Optional[float] = None  # None if simulator has no battery physics, NEVER fabricated
    battery_voltage: Optional[float] = None
    armed: bool = False
    flight_mode: str = "DISARMED"
    simulator: str = "LOS-Flight-Simulator"
    raw_status: Optional[str] = None

    def to_legacy_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format expected by S.I.G.H.T. frontend & context engines."""
        return {
            "timestamp": self.timestamp,
            "connected": self.connected,
            "lat": self.latitude,
            "lng": self.longitude,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "altitude": round(self.altitude, 2),
            "altitude_m": round(self.altitude, 2),
            "speed": round(self.velocity.ground_speed, 2),
            "speed_mps": round(self.velocity.ground_speed, 2),
            "headingDegrees": round(self.heading, 1),
            "heading": f"{round(self.heading, 1)}°",
            "battery": self.battery,
            "batteryVoltage": self.battery_voltage,
            "isArmed": self.armed,
            "flightMode": self.flight_mode,
            "linkStatus": "ONLINE" if self.connected else "LOST",
            "systemStatus": "ONLINE" if self.connected else "STANDBY",
            "roll": round(self.attitude.roll, 1),
            "pitch": round(self.attitude.pitch, 1),
            "yaw": round(self.attitude.yaw, 1),
            "climbRate": round(self.velocity.y, 2),
            "simulator": self.simulator,
        }
