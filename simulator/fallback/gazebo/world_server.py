"""
PROJECT S.I.G.H.T. - Gazebo Synthetic World Simulation
Maintains physical coordinates of perimeter terrain, priority zones,
and ground targets (Person, Vehicle, Animal) within the 3D world space.
"""

import math
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple

@dataclass
class WorldEntity:
    id: str
    object_class: str # "Person", "Vehicle", "Animal"
    lat: float
    lng: float
    altitude_m: float = 0.0
    heading_deg: float = 0.0
    speed_mps: float = 0.0
    bounding_box_size: Tuple[float, float, float] = (4.5, 2.0, 1.6) # L, W, H in meters
    zone_name: str = "Unassigned"
    is_priority_zone: bool = False

class GazeboWorldServer:
    """
    Simulates the physical environment and entities of the proving ground world.
    """
    def __init__(self):
        self.world_origin = (34.0522, -117.8247)
        self.entities: Dict[str, WorldEntity] = {}
        self._init_default_world_entities()

    def _init_default_world_entities(self):
        # 1. Patrol vehicle inside Priority Zone Alpha (North Ridge Access Road)
        self.entities["VEH-01"] = WorldEntity(
            id="VEH-01",
            object_class="Vehicle",
            lat=34.0621,
            lng=-117.8038,
            speed_mps=6.5,
            zone_name="Priority Zone Alpha",
            is_priority_zone=True,
            bounding_box_size=(4.8, 2.0, 1.7)
        )

        # 2. Person loitering outside priority zone (Buffer Zone West)
        self.entities["PER-01"] = WorldEntity(
            id="PER-01",
            object_class="Person",
            lat=34.0572,
            lng=-117.8184,
            speed_mps=1.2,
            zone_name="Outside Priority Zone",
            is_priority_zone=False,
            bounding_box_size=(0.6, 0.5, 1.8)
        )

        # 3. Wildlife/Animal in canyon scrub brush (irrelevant to mission)
        self.entities["ANI-01"] = WorldEntity(
            id="ANI-01",
            object_class="Animal",
            lat=34.0531,
            lng=-117.8220,
            speed_mps=0.8,
            zone_name="Outside Mission Relevance",
            is_priority_zone=False,
            bounding_box_size=(1.5, 0.6, 1.1)
        )

        # 4. Secondary vehicle approaching Perimeter East Gate
        self.entities["VEH-02"] = WorldEntity(
            id="VEH-02",
            object_class="Vehicle",
            lat=34.0535,
            lng=-117.8075,
            speed_mps=4.0,
            zone_name="Priority Zone Beta",
            is_priority_zone=True,
            bounding_box_size=(5.2, 2.2, 2.0)
        )

    def get_entities_in_camera_fov(
        self,
        uav_lat: float,
        uav_lng: float,
        uav_alt_m: float,
        uav_heading_deg: float,
        hfov_deg: float = 75.0,
        vfov_deg: float = 55.0
    ) -> List[Dict[str, Any]]:
        """
        Calculates which world entities project onto the downward-facing gimbal camera sensor.
        Returns pixel bounding box projections (norm_x, norm_y, norm_w, norm_h in range [0, 1]).
        """
        visible_targets = []
        if uav_alt_m < 5.0:
            return self._get_stationary_verification_targets()

        # Ground footprint radius in meters
        ground_radius_x = uav_alt_m * math.tan(math.radians(hfov_deg / 2.0))
        ground_radius_y = uav_alt_m * math.tan(math.radians(vfov_deg / 2.0))

        for entity_id, entity in self.entities.items():
            # Delta in meters from UAV
            d_north_m = (entity.lat - uav_lat) * 111139.0
            d_east_m = (entity.lng - uav_lng) * (111139.0 * math.cos(math.radians(uav_lat)))

            # Rotate delta into UAV body frame (aligned with heading)
            hdg_rad = math.radians(uav_heading_deg)
            # Body forward (Y) and Body right (X)
            y_body = d_north_m * math.cos(hdg_rad) + d_east_m * math.sin(hdg_rad)
            x_body = -d_north_m * math.sin(hdg_rad) + d_east_m * math.cos(hdg_rad)

            # Check if within camera field of view
            if abs(x_body) <= ground_radius_x and abs(y_body) <= ground_radius_y:
                # Normalized coordinates (0, 0 is top-left, 1, 1 is bottom-right)
                norm_x = (x_body / (2.0 * ground_radius_x)) + 0.5
                norm_y = (-y_body / (2.0 * ground_radius_y)) + 0.5

                # Projected bounding box scale inversely proportional to altitude
                pixel_scale = 1.0 / max(10.0, uav_alt_m)
                norm_w = min(0.4, max(0.04, (entity.bounding_box_size[0] / ground_radius_x) * 0.5))
                norm_h = min(0.4, max(0.04, (entity.bounding_box_size[1] / ground_radius_y) * 0.5))

                visible_targets.append({
                    "entity_id": entity.id,
                    "class": entity.object_class,
                    "lat": entity.lat,
                    "lng": entity.lng,
                    "zone": entity.zone_name,
                    "is_priority_zone": entity.is_priority_zone,
                    "norm_bbox": (norm_x, norm_y, norm_w, norm_h),
                    "distance_m": round(math.sqrt(d_north_m**2 + d_east_m**2), 1)
                })

        return visible_targets

    def _get_stationary_verification_targets(self) -> List[Dict[str, Any]]:
        """Provide deterministic fallback observations without changing flight state."""
        return [
            {
                "entity_id": "ANI-01",
                "class": "Animal",
                "lat": 34.0523,
                "lng": -117.8246,
                "zone": "Outside Mission Relevance",
                "is_priority_zone": False,
                "norm_bbox": (0.35, 0.45, 0.12, 0.12),
                "distance_m": 15.0,
            },
            {
                "entity_id": "PER-01",
                "class": "Person",
                "lat": 34.0524,
                "lng": -117.8245,
                "zone": "Outside Priority Zone",
                "is_priority_zone": False,
                "norm_bbox": (0.65, 0.5, 0.08, 0.2),
                "distance_m": 25.0,
            },
        ]
