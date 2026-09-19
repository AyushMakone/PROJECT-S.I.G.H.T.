"""
PROJECT S.I.G.H.T. — Simulator Configuration Module
Defines operational parameters for the primary Online Drone Simulator.
"""

import os
from dataclasses import dataclass


@dataclass
class SimulatorConfig:
    """Configuration for the S.I.G.H.T. drone simulator subsystem."""

    # Mode: 'online' (authoritative production), 'fallback' (offline dev only)
    mode: str = os.getenv("SIMULATOR_MODE", "online").lower()

    # Provider name
    provider: str = os.getenv("SIMULATOR_PROVIDER", "LOS-Flight-Simulator")

    # Online Simulator Host endpoints (never default to hardcoded localhost in prod)
    host_url: str = os.getenv("SIMULATOR_URL", "http://127.0.0.1:8080")
    ws_url: str = os.getenv("SIMULATOR_WS_URL", "ws://127.0.0.1:8080/ws/telemetry")

    # API credentials if secured
    api_key: str = os.getenv("SIMULATOR_API_KEY", "")

    # Telemetry and streaming parameters
    telemetry_rate_hz: float = float(os.getenv("SIMULATOR_TELEMETRY_RATE_HZ", "10.0"))
    stale_timeout_s: float = float(os.getenv("SIMULATOR_STALE_TIMEOUT_S", "2.5"))
    camera_fps: int = int(os.getenv("SIMULATOR_CAMERA_FPS", "15"))

    # Origin coordinates for local ENU -> GPS projection
    base_latitude: float = float(os.getenv("SIMULATOR_BASE_LAT", "28.7041"))
    base_longitude: float = float(os.getenv("SIMULATOR_BASE_LNG", "77.1025"))

    @classmethod
    def from_env(cls) -> "SimulatorConfig":
        return cls()


config = SimulatorConfig.from_env()
