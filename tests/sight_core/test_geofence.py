"""
test_geofence.py
Unit tests for GeofenceClassifier — raycasting point-in-polygon
and AABB pre-filter accuracy.
"""

import pytest
from sight_core.context.geofence import GeofenceClassifier
from sight_core.models.mission_card import PriorityZone


# ─────────────────────────────────────────────
#  Test Polygons
# ─────────────────────────────────────────────

# Simple axis-aligned rectangle:
# lat ∈ [28.70, 28.72], lng ∈ [77.10, 77.13]
SQUARE_POLYGON = [
    (28.70, 77.10),
    (28.72, 77.10),
    (28.72, 77.13),
    (28.70, 77.13),
]

# Irregular convex pentagon
PENTAGON_POLYGON = [
    (28.75, 77.20),
    (28.77, 77.22),
    (28.76, 77.25),
    (28.73, 77.25),
    (28.72, 77.22),
]

# Priority zones list for check_priority_zones tests
ZONE_ALPHA = PriorityZone(
    id="ZONE-A",
    name="Zone Alpha",
    polygon=SQUARE_POLYGON,
)

ZONE_BETA = PriorityZone(
    id="ZONE-B",
    name="Zone Beta (Pentagon)",
    polygon=PENTAGON_POLYGON,
)


# ─────────────────────────────────────────────
#  Point-in-Polygon: Axis-aligned square
# ─────────────────────────────────────────────

class TestIsPointInPolygonSquare:
    def test_centroid_inside(self):
        assert GeofenceClassifier.is_point_in_polygon(28.71, 77.115, SQUARE_POLYGON) is True

    def test_interior_point_inside(self):
        assert GeofenceClassifier.is_point_in_polygon(28.705, 77.105, SQUARE_POLYGON) is True

    def test_point_outside_north(self):
        assert GeofenceClassifier.is_point_in_polygon(28.73, 77.115, SQUARE_POLYGON) is False

    def test_point_outside_south(self):
        assert GeofenceClassifier.is_point_in_polygon(28.69, 77.115, SQUARE_POLYGON) is False

    def test_point_outside_east(self):
        assert GeofenceClassifier.is_point_in_polygon(28.71, 77.15, SQUARE_POLYGON) is False

    def test_point_outside_west(self):
        assert GeofenceClassifier.is_point_in_polygon(28.71, 77.09, SQUARE_POLYGON) is False

    def test_point_far_outside(self):
        assert GeofenceClassifier.is_point_in_polygon(0.0, 0.0, SQUARE_POLYGON) is False


# ─────────────────────────────────────────────
#  AABB Pre-filter
# ─────────────────────────────────────────────

class TestAABBPreFilter:
    def test_aabb_rejects_far_outside_quickly(self):
        """Point well outside bounding box — AABB must reject before raycasting."""
        result = GeofenceClassifier.is_point_in_polygon(50.0, 100.0, SQUARE_POLYGON)
        assert result is False

    def test_aabb_passes_interior_to_raycast(self):
        """Point inside bounding box — reaches raycasting layer and returns True."""
        result = GeofenceClassifier.is_point_in_polygon(28.71, 77.115, SQUARE_POLYGON)
        assert result is True


# ─────────────────────────────────────────────
#  Point-in-Polygon: Pentagon (non-convex edges)
# ─────────────────────────────────────────────

class TestIsPointInPolygonPentagon:
    def test_centroid_inside_pentagon(self):
        # Approximate centroid of pentagon
        assert GeofenceClassifier.is_point_in_polygon(28.746, 77.228, PENTAGON_POLYGON) is True

    def test_outside_pentagon_returns_false(self):
        assert GeofenceClassifier.is_point_in_polygon(28.80, 77.28, PENTAGON_POLYGON) is False


# ─────────────────────────────────────────────
#  Degenerate Polygon Guards
# ─────────────────────────────────────────────

class TestDegeneratePolygons:
    def test_polygon_with_two_vertices_returns_false(self):
        degenerate = [(28.70, 77.10), (28.72, 77.10)]
        assert GeofenceClassifier.is_point_in_polygon(28.71, 77.10, degenerate) is False

    def test_empty_polygon_returns_false(self):
        assert GeofenceClassifier.is_point_in_polygon(28.71, 77.10, []) is False


# ─────────────────────────────────────────────
#  check_priority_zones
# ─────────────────────────────────────────────

class TestCheckPriorityZones:
    def test_point_inside_zone_alpha(self):
        inside, name = GeofenceClassifier.check_priority_zones(
            28.71, 77.115, [ZONE_ALPHA, ZONE_BETA]
        )
        assert inside is True
        assert name == "Zone Alpha"

    def test_point_inside_zone_beta(self):
        inside, name = GeofenceClassifier.check_priority_zones(
            28.746, 77.228, [ZONE_ALPHA, ZONE_BETA]
        )
        assert inside is True
        assert name == "Zone Beta (Pentagon)"

    def test_point_outside_all_zones(self):
        inside, name = GeofenceClassifier.check_priority_zones(
            0.0, 0.0, [ZONE_ALPHA, ZONE_BETA]
        )
        assert inside is False
        assert name is None

    def test_empty_zones_list_returns_false(self):
        inside, name = GeofenceClassifier.check_priority_zones(28.71, 77.115, [])
        assert inside is False
        assert name is None

    def test_first_matching_zone_returned(self):
        """When point matches multiple (overlapping) zones, first in list is returned."""
        # Two identical zones — first should be returned
        zone_dup = PriorityZone(id="ZONE-DUP", name="Duplicate", polygon=SQUARE_POLYGON)
        inside, name = GeofenceClassifier.check_priority_zones(
            28.71, 77.115, [ZONE_ALPHA, zone_dup]
        )
        assert inside is True
        assert name == "Zone Alpha"
