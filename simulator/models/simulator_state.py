"""
PROJECT S.I.G.H.T. — Simulator State Models
Tracks connection health, latency, provider metadata, and operational status.
"""

from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field


class ConnectionState(str, Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    CONNECTING = "CONNECTING"
    DISCONNECTED = "DISCONNECTED"
    STALE = "STALE"


# Alias used by OnlineSimulatorAdapter
SimulatorConnectionState = ConnectionState


class SimulatorState(BaseModel):
    status: ConnectionState = ConnectionState.OFFLINE
    provider: str = "LOS-Flight-Simulator"
    connection_type: str = "WebSocket / HTTP"
    host_url: str = ""
    latency_ms: float = 0.0
    telemetry_frequency_hz: float = 0.0
    last_heartbeat_timestamp: Optional[str] = None
    is_armed: bool = False
    flight_mode: str = "DISARMED"
    message: Optional[str] = None
