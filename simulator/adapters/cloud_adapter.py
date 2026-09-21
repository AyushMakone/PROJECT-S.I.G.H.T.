"""
PROJECT S.I.G.H.T. — Cloud Drone Simulator Adapter
Connects S.I.G.H.T. to cloud-hosted PX4 SITL instances or remote Linux VM simulators.
"""

import os
import time
import asyncio
import logging
from typing import Dict, Any, Optional
import numpy as np

from .px4_adapter import PX4Adapter

logger = logging.getLogger("SIGHT.CloudAdapter")


class CloudAdapter(PX4Adapter):
    """
    Adapter tailored for remote cloud-hosted UAV simulators.
    Extends PX4Adapter with cloud network resilience, latency metrics, and API hooks.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        mavlink_endpoint: Optional[str] = None,
        camera_url: Optional[str] = None
    ):
        self.host = host or os.getenv("SIMULATOR_HOST", "cloud.sight-uav.net")
        self.port = port or int(os.getenv("SIMULATOR_PORT", "14550"))
        self.camera_url = camera_url or os.getenv("CAMERA_URL", "")

        # Explicit cloud host/port should always win over any ambient MAVLINK_ENDPOINT
        # environment value. This prevents the local ArduPilot SITL route from being
        # mistakenly reused when the code is intentionally connecting to a remote cloud host.
        if mavlink_endpoint is not None:
            endpoint = mavlink_endpoint
        elif host is not None or port is not None:
            endpoint = f"udpout:{self.host}:{self.port}"
        else:
            endpoint = os.getenv("MAVLINK_ENDPOINT")
            if not endpoint:
                # If a remote IP or hostname is specified, default to UDP or TCP connection
                if self.host in ["127.0.0.1", "localhost", "0.0.0.0"]:
                    endpoint = f"udpin:0.0.0.0:{self.port}"
                else:
                    endpoint = f"udpout:{self.host}:{self.port}"

        super().__init__(connection_string=endpoint)
        self._round_trip_latency_ms = 0.0

    @property
    def mode_name(self) -> str:
        return "cloud"

    async def connect(self) -> bool:
        logger.info(f"[SIM] Connecting to Cloud Simulator at {self.host}:{self.port} (endpoint: {self.connection_string})...")
        success = await super().connect()
        if success:
            logger.info(f"[SIM] Connected to Cloud Simulator ({self.host}).")
        else:
            logger.warning(f"[SIM] Cloud connection attempt timed out or failed to connect to {self.connection_string}.")
        return success

    async def get_telemetry(self) -> Dict[str, Any]:
        """Adds cloud network telemetry (latency, remote endpoint) to standard schema."""
        telem = await super().get_telemetry()
        telem["cloudHost"] = self.host
        telem["latencyMs"] = round(self._round_trip_latency_ms, 1)
        return telem
