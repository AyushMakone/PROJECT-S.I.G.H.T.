"""
PROJECT S.I.G.H.T.
Synthetic camera provider.

Connects real SITL telemetry to the synthetic world camera.
"""

import asyncio
import logging
import time
from typing import Optional

import numpy as np

from simulator.geo.coordinate_transform import CoordinateTransform
from simulator.gazebo.camera_sensor import UAVCameraSensor
from simulator.gazebo.world_server import GazeboWorldServer

logger = logging.getLogger("SIGHT.SyntheticCameraProvider")


class SyntheticCameraProvider:
    """
    Generates camera frames from the real UAV pose reported by SITL.

    Flow:
        SITL telemetry
            ?
        CoordinateTransform
            ?
        Synthetic world
            ?
        UAVCameraSensor
            ?
        camera frame
    """

    def __init__(
        self,
        adapter,
        width: int = 640,
        height: int = 480,
        fps: int = 15,
    ):
        self.adapter = adapter

        self.world = GazeboWorldServer()

        self.sensor = UAVCameraSensor(
            world=self.world,
            width=width,
            height=height,
            fps=fps,
        )

        self._latest_frame: Optional[np.ndarray] = None
        self._last_capture_time = 0.0
        self._min_frame_interval = 1.0 / max(1, fps)

    async def get_latest_frame(self) -> Optional[np.ndarray]:
        """
        Generate and return the latest synthetic camera frame.
        """

        telemetry = getattr(self.adapter, "telemetry", None)
        if isinstance(telemetry, dict):
            latitude = telemetry.get("latitude")
            longitude = telemetry.get("longitude")
            altitude = telemetry.get("relative_altitude_m")
            heading = telemetry.get("heading_deg")
        else:
            latitude = getattr(telemetry, "latitude", None)
            longitude = getattr(telemetry, "longitude", None)
            altitude = getattr(telemetry, "relative_altitude_m", None)
            heading = getattr(telemetry, "heading_deg", None)

        if latitude is None or longitude is None:
            return self._latest_frame

        if altitude is None:
            altitude = 0.0

        if heading is None:
            heading = 0.0

        now = time.time()

        # Prevent unnecessary rendering.
        if (
            self._latest_frame is not None
            and (now - self._last_capture_time)
            < self._min_frame_interval
        ):
            return self._latest_frame

        # Convert real SITL GPS coordinates into
        # the synthetic world's coordinate system.
        world_lat, world_lng = (
            CoordinateTransform.sitl_gps_to_world_gps(
                latitude,
                longitude,
            )
        )

        # Render the synthetic optical frame.
        frame = self.sensor.capture_frame(
            uav_lat=world_lat,
            uav_lng=world_lng,
            uav_alt_m=altitude,
            uav_heading_deg=heading,
            target_timestamp=now,
        )

        if frame is not None:
            self._latest_frame = frame
            self._last_capture_time = now

        return self._latest_frame

    def get_visible_targets(
        self,
        latitude: float,
        longitude: float,
        altitude_m: float,
        heading_deg: float,
    ):
        """Return read-only synthetic-world visibility for the current UAV pose."""
        world_lat, world_lng = CoordinateTransform.sitl_gps_to_world_gps(
            latitude,
            longitude,
        )
        return self.world.get_entities_in_camera_fov(
            uav_lat=world_lat,
            uav_lng=world_lng,
            uav_alt_m=altitude_m,
            uav_heading_deg=heading_deg,
            hfov_deg=self.sensor.hfov_deg,
            vfov_deg=self.sensor.vfov_deg,
        )
