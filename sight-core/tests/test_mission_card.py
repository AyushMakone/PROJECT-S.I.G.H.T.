"""
test_mission_card.py
Unit tests for MissionCard and PriorityZone Pydantic models.
Validates field constraints, defaults, serialization, and edge cases.
"""

import pytest
from pydantic import ValidationError
from sight_core.models.mission_card import MissionCard, PriorityZone


# ─────────────────────────────────────────────
#  Fixtures
# ─────────────────────────────────────────────

VALID_ZONE_DATA = {
    "id": "ZONE-A",
    "name": "Zone Alpha (North Ridge)",
    "polygon": [
        (28.70, 77.10),
        (28.72, 77.10),
        (28.72, 77.13),
        (28.70, 77.13),
    ],
    "description": "Northern ridge surveillance sector",
}

VALID_CARD_DATA = {
    "missionId": "SIGHT-M01",
    "objective": "Perimeter Surveillance",
    "relevantObjects": ["Person", "Vehicle"],
    "persistenceFrames": 2,
    "evidence": "Disabled",
    "communicationPolicy": "EVENT ONLY",
    "batteryRthPercent": 20.0,
    "minConfidencePercent": 60.0,
    "priorityZones": [VALID_ZONE_DATA],
}


# ─────────────────────────────────────────────
#  PriorityZone Tests
# ─────────────────────────────────────────────

class TestPriorityZone:
    def test_valid_zone_creates_successfully(self):
        zone = PriorityZone(**VALID_ZONE_DATA)
        assert zone.id == "ZONE-A"
        assert zone.name == "Zone Alpha (North Ridge)"
        assert len(zone.polygon) == 4

    def test_zone_polygon_too_few_vertices_raises(self):
        data = dict(VALID_ZONE_DATA)
        data["polygon"] = [(28.70, 77.10), (28.72, 77.10)]  # only 2 points
        with pytest.raises(ValidationError, match="at least 3"):
            PriorityZone(**data)

    def test_zone_invalid_latitude_raises(self):
        data = dict(VALID_ZONE_DATA)
        data["polygon"] = [(95.0, 77.10), (28.72, 77.10), (28.72, 77.13)]  # lat > 90
        with pytest.raises(ValidationError, match="Invalid coordinate"):
            PriorityZone(**data)

    def test_zone_invalid_longitude_raises(self):
        data = dict(VALID_ZONE_DATA)
        data["polygon"] = [(28.70, 200.0), (28.72, 77.10), (28.72, 77.13)]  # lng > 180
        with pytest.raises(ValidationError, match="Invalid coordinate"):
            PriorityZone(**data)

    def test_zone_optional_description_defaults_empty(self):
        data = dict(VALID_ZONE_DATA)
        del data["description"]
        zone = PriorityZone(**data)
        assert zone.description == ""


# ─────────────────────────────────────────────
#  MissionCard Tests
# ─────────────────────────────────────────────

class TestMissionCard:
    def test_valid_card_creates_successfully(self):
        card = MissionCard(**VALID_CARD_DATA)
        assert card.mission_id == "SIGHT-M01"
        assert card.objective == "Perimeter Surveillance"
        assert "Person" in card.relevant_objects
        assert card.persistence_frames == 2
        assert card.battery_rth_percent == 20.0
        assert card.min_confidence_percent == 60.0

    def test_default_uav_id(self):
        card = MissionCard(**VALID_CARD_DATA)
        assert card.uav_id == "SIGHT-UAV-01"

    def test_default_relevant_objects(self):
        data = dict(VALID_CARD_DATA)
        del data["relevantObjects"]
        card = MissionCard(**data)
        assert "Person" in card.relevant_objects
        assert "Vehicle" in card.relevant_objects

    def test_battery_rth_too_low_raises(self):
        data = dict(VALID_CARD_DATA)
        data["batteryRthPercent"] = 3.0  # Below 5.0 minimum
        with pytest.raises(ValidationError, match="between 5%"):
            MissionCard(**data)

    def test_battery_rth_too_high_raises(self):
        data = dict(VALID_CARD_DATA)
        data["batteryRthPercent"] = 55.0  # Above 50.0 maximum
        with pytest.raises(ValidationError, match="between 5%"):
            MissionCard(**data)

    def test_battery_rth_boundary_low_accepted(self):
        data = dict(VALID_CARD_DATA)
        data["batteryRthPercent"] = 5.0
        card = MissionCard(**data)
        assert card.battery_rth_percent == 5.0

    def test_battery_rth_boundary_high_accepted(self):
        data = dict(VALID_CARD_DATA)
        data["batteryRthPercent"] = 50.0
        card = MissionCard(**data)
        assert card.battery_rth_percent == 50.0

    def test_persistence_frames_zero_raises(self):
        data = dict(VALID_CARD_DATA)
        data["persistenceFrames"] = 0
        with pytest.raises(ValidationError, match="at least 1"):
            MissionCard(**data)

    def test_persistence_frames_minimum_accepted(self):
        data = dict(VALID_CARD_DATA)
        data["persistenceFrames"] = 1
        card = MissionCard(**data)
        assert card.persistence_frames == 1

    def test_evidence_enabled(self):
        data = dict(VALID_CARD_DATA)
        data["evidence"] = "Enabled"
        card = MissionCard(**data)
        assert card.evidence == "Enabled"

    def test_communication_policy_silent(self):
        data = dict(VALID_CARD_DATA)
        data["communicationPolicy"] = "SILENT"
        card = MissionCard(**data)
        assert card.communication_policy == "SILENT"

    def test_multiple_priority_zones(self):
        zone_b = {
            "id": "ZONE-B",
            "name": "Zone Beta (East Gate)",
            "polygon": [(28.68, 77.14), (28.70, 77.14), (28.70, 77.16), (28.68, 77.16)],
        }
        data = dict(VALID_CARD_DATA)
        data["priorityZones"] = [VALID_ZONE_DATA, zone_b]
        card = MissionCard(**data)
        assert len(card.priority_zones) == 2

    def test_snake_case_field_access(self):
        """Test that both alias and snake_case field access work."""
        card = MissionCard(**VALID_CARD_DATA)
        assert card.mission_id == "SIGHT-M01"
        assert card.relevant_objects == ["Person", "Vehicle"]
