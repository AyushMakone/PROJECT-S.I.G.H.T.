"""
PROJECT S.I.G.H.T.
Coordinate transform between real SITL GPS coordinates
and the synthetic simulator world.

The SITL home position is the reference point.
The synthetic world origin is where the procedural world is rendered.
"""

import math
from typing import Tuple

from simulator.config.simulator_config import config


class CoordinateTransform:
    """Convert between GPS coordinates and local North/East metres."""

    # Synthetic world origin used by GazeboWorldServer.
    WORLD_ORIGIN_LAT = 34.0522
    WORLD_ORIGIN_LNG = -117.8247

    METERS_PER_DEG_LAT = 111_139.0

    @classmethod
    def gps_to_local_ne(
        cls,
        latitude: float,
        longitude: float,
    ) -> Tuple[float, float]:
        """
        Convert GPS coordinates into local North/East metres
        relative to the configured SITL base position.
        """
        d_north = (
            latitude - config.base_latitude
        ) * cls.METERS_PER_DEG_LAT

        d_east = (
            longitude - config.base_longitude
        ) * (
            cls.METERS_PER_DEG_LAT
            * math.cos(math.radians(config.base_latitude))
        )

        return d_north, d_east

    @classmethod
    def local_ne_to_world_gps(
        cls,
        north_m: float,
        east_m: float,
    ) -> Tuple[float, float]:
        """
        Convert local North/East metres into the synthetic
        world's GPS coordinate system.
        """
        world_lat = (
            cls.WORLD_ORIGIN_LAT
            + north_m / cls.METERS_PER_DEG_LAT
        )

        world_lng = (
            cls.WORLD_ORIGIN_LNG
            + east_m / (
                cls.METERS_PER_DEG_LAT
                * math.cos(math.radians(cls.WORLD_ORIGIN_LAT))
            )
        )

        return world_lat, world_lng

    @classmethod
    def sitl_gps_to_world_gps(
        cls,
        latitude: float,
        longitude: float,
    ) -> Tuple[float, float]:
        """
        Convert a real SITL GPS position directly into the
        corresponding synthetic-world GPS position.
        """
        north_m, east_m = cls.gps_to_local_ne(latitude, longitude)

        return cls.local_ne_to_world_gps(
            north_m,
            east_m,
        )