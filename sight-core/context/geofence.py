"""
PROJECT S.I.G.H.T. Core - Spatial Geofence Classifier
Provides raycasting point-in-polygon algorithms with Axis-Aligned Bounding Box (AABB)
pre-filtering for real-time edge spatial classification.
"""

from typing import List, Tuple, Optional
from ..models.mission_card import PriorityZone

class GeofenceClassifier:
    """
    Evaluates whether target coordinates lie inside priority zones or operational areas.
    """
    @staticmethod
    def is_point_in_polygon(lat: float, lng: float, polygon: List[Tuple[float, float]]) -> bool:
        """
        Raycasting algorithm to determine if a point (lat, lng) is inside polygon.
        Polygon is a list of (lat, lng) tuples.
        """
        n = len(polygon)
        if n < 3:
            return False

        # 1. Quick AABB pre-check
        lats = [p[0] for p in polygon]
        lngs = [p[1] for p in polygon]
        if lat < min(lats) or lat > max(lats) or lng < min(lngs) or lng > max(lngs):
            return False

        # 2. Raycasting test
        inside = False
        p1_lat, p1_lng = polygon[0]
        for i in range(1, n + 1):
            p2_lat, p2_lng = polygon[i % n]
            
            # Check if horizontal ray crosses segment p1-p2
            if min(p1_lat, p2_lat) < lat <= max(p1_lat, p2_lat):
                if lng <= max(p1_lng, p2_lng):
                    if p1_lat != p2_lat:
                        x_inters = (lat - p1_lat) * (p2_lng - p1_lng) / (p2_lat - p1_lat) + p1_lng
                        if p1_lng == p2_lng or lng <= x_inters:
                            inside = not inside
            p1_lat, p1_lng = p2_lat, p2_lng

        return inside

    @classmethod
    def check_priority_zones(
        cls,
        lat: float,
        lng: float,
        zones: List[PriorityZone]
    ) -> Tuple[bool, Optional[str]]:
        """
        Returns (is_inside, zone_name).
        """
        for zone in zones:
            if cls.is_point_in_polygon(lat, lng, zone.polygon):
                return True, zone.name
        return False, None
