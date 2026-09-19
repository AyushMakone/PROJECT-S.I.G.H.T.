"""
PROJECT S.I.G.H.T. — Mission Loader
Parses and validates waypoint mission definitions for simulated flight execution.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

logger = logging.getLogger("SIGHT.MissionLoader")


@dataclass
class SimulatorWaypoint:
    id: str
    name: str
    lat: float
    lng: float
    altitude_m: float = 80.0
    speed_mps: float = 12.0
    acceptance_radius_m: float = 8.0
    is_priority_zone: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "lat": self.lat,
            "lng": self.lng,
            "altitude_m": self.altitude_m,
            "speed_mps": self.speed_mps,
            "acceptance_radius_m": self.acceptance_radius_m,
            "is_priority_zone": self.is_priority_zone
        }


class MissionLoader:
    """Loads and validates waypoint missions from JSON files."""

    @staticmethod
    def load_from_file(filepath: str) -> List[SimulatorWaypoint]:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Mission file not found: {filepath}")

        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        return MissionLoader.parse_dict(data)

    @staticmethod
    def parse_dict(data: Dict[str, Any]) -> List[SimulatorWaypoint]:
        waypoints = []
        raw_wps = data.get("waypoints", [])

        for item in raw_wps:
            wp = SimulatorWaypoint(
                id=str(item.get("id", f"WP-{len(waypoints)+1:02d}")),
                name=str(item.get("name", f"Waypoint {len(waypoints)+1}")),
                lat=float(item.get("lat", 0.0)),
                lng=float(item.get("lng", 0.0)),
                altitude_m=float(item.get("altitude_m", 80.0)),
                speed_mps=float(item.get("speed_mps", 12.0)),
                acceptance_radius_m=float(item.get("acceptance_radius_m", 8.0)),
                is_priority_zone=bool(item.get("is_priority_zone", False))
            )
            waypoints.append(wp)

        logger.info(f"[SIM] Loaded {len(waypoints)} waypoints from mission data.")
        return waypoints
