"""
test_governor_decisions.py
Integration tests for the S.I.G.H.T. Governor Engine.
Verifies all 4 decision states across the full 8-step evaluation hierarchy.

Decision matrix covered:
  Rule 1: comm link unavailable                     → RETAIN
  Rule 2: battery <= RTH threshold                  → RETAIN
  Rule 3: irrelevant object class                   → SUPPRESS
  Rule 4: confidence below minimum                  → RETAIN
  Rule 5: relevant target outside priority zone     → RETAIN
  Rule 6: target in zone, persistence not met       → RETAIN
  Rule 7: evidence policy active                    → EVIDENCE
  Rule 8: all conditions satisfied, no evidence     → EVENT
"""

import pytest
from sight_core.models.mission_card import MissionCard, PriorityZone
from sight_core.models.detection import PerceptionDetection
from sight_core.mission.mission_card_manager import MissionCardManager
from sight_core.context.context_engine import ContextEngine
from sight_core.governor.governor_engine import GovernorEngine


# ─────────────────────────────────────────────
#  Shared Test Fixtures
# ─────────────────────────────────────────────

# A simple rectangle zone at lat∈[28.70, 28.72], lng∈[77.10, 77.13]
ZONE_ALPHA = PriorityZone(
    id="ZONE-A",
    name="Zone Alpha",
    polygon=[
        (28.70, 77.10),
        (28.72, 77.10),
        (28.72, 77.13),
        (28.70, 77.13),
    ],
)

# Coordinates: inside Zone Alpha centroid
INSIDE_LAT, INSIDE_LNG = 28.71, 77.115

# Coordinates: clearly outside Zone Alpha
OUTSIDE_LAT, OUTSIDE_LNG = 0.0, 0.0


def make_card(
    evidence: str = "Disabled",
    persistence_frames: int = 2,
    battery_rth_percent: float = 20.0,
    min_confidence: float = 60.0,
    relevant_objects: list = None,
    comm_policy: str = "EVENT ONLY",
) -> MissionCard:
    """Helper to create a MissionCard with a single priority zone."""
    return MissionCard(
        **{
            "missionId": "TEST-M01",
            "objective": "Test Mission",
            "relevantObjects": relevant_objects or ["Person", "Vehicle"],
            "persistenceFrames": persistence_frames,
            "evidence": evidence,
            "communicationPolicy": comm_policy,
            "batteryRthPercent": battery_rth_percent,
            "minConfidencePercent": min_confidence,
            "priorityZones": [ZONE_ALPHA.model_dump()],
        }
    )


def make_detection(
    object_class: str = "Person",
    confidence: float = 85.0,
    lat: float = INSIDE_LAT,
    lng: float = INSIDE_LNG,
    persistence: int = 3,
) -> PerceptionDetection:
    """Helper to create a passing PerceptionDetection."""
    return PerceptionDetection(
        **{
            "id": "DET-001",
            "objectClass": object_class,
            "confidence": confidence,
            "normBbox": (0.4, 0.4, 0.1, 0.2),
            "trackId": 1,
            "persistence": persistence,
            "lat": lat,
            "lng": lng,
            "altitudeM": 50.0,
            "timestamp": "12:00:00 UTC",
        }
    )


def make_governor(card: MissionCard) -> GovernorEngine:
    """Helper to assemble full GovernorEngine from a MissionCard."""
    manager = MissionCardManager(initial_card=card)
    context_engine = ContextEngine(mission_manager=manager)
    return GovernorEngine(context_engine=context_engine)


# ─────────────────────────────────────────────
#  Rule 1: Communication Unavailable → RETAIN
# ─────────────────────────────────────────────

class TestRule1CommUnavailable:
    def test_comm_down_returns_retain(self):
        governor = make_governor(make_card())
        detection = make_detection()
        result = governor.evaluate(detection, uav_battery_percent=80.0, communication_available=False)
        assert result.decision == "RETAIN"
        assert "communication" in result.reason.lower()
        assert result.evaluated_conditions.communication_available is False

    def test_comm_down_overrides_all_other_conditions(self):
        """Even with all other conditions optimal, RETAIN if comm is down."""
        governor = make_governor(make_card(evidence="Enabled"))
        detection = make_detection(confidence=99.0, persistence=10)
        result = governor.evaluate(detection, uav_battery_percent=95.0, communication_available=False)
        assert result.decision == "RETAIN"


# ─────────────────────────────────────────────
#  Rule 2: Battery at/below RTH → RETAIN
# ─────────────────────────────────────────────

class TestRule2BatteryLow:
    def test_battery_at_rth_returns_retain(self):
        governor = make_governor(make_card(battery_rth_percent=20.0))
        detection = make_detection()
        result = governor.evaluate(detection, uav_battery_percent=20.0, communication_available=True)
        assert result.decision == "RETAIN"
        assert "battery" in result.reason.lower()

    def test_battery_below_rth_returns_retain(self):
        governor = make_governor(make_card(battery_rth_percent=20.0))
        detection = make_detection()
        result = governor.evaluate(detection, uav_battery_percent=15.0, communication_available=True)
        assert result.decision == "RETAIN"

    def test_battery_above_rth_does_not_trigger(self):
        governor = make_governor(make_card(battery_rth_percent=20.0))
        detection = make_detection()
        result = governor.evaluate(detection, uav_battery_percent=50.0, communication_available=True)
        # Should not be RETAIN due to battery (may be EVENT if all else passes)
        assert result.evaluated_conditions.battery_above_threshold is True

    def test_battery_one_percent_above_rth_passes(self):
        governor = make_governor(make_card(battery_rth_percent=20.0))
        detection = make_detection()
        result = governor.evaluate(detection, uav_battery_percent=20.1, communication_available=True)
        assert result.evaluated_conditions.battery_above_threshold is True


# ─────────────────────────────────────────────
#  Rule 3: Irrelevant Object → SUPPRESS
# ─────────────────────────────────────────────

class TestRule3IrrelevantObject:
    def test_animal_suppressed_for_perimeter_mission(self):
        governor = make_governor(make_card(relevant_objects=["Person", "Vehicle"]))
        detection = make_detection(object_class="Animal")
        result = governor.evaluate(detection, uav_battery_percent=80.0, communication_available=True)
        assert result.decision == "SUPPRESS"
        assert "Animal" in result.reason or "animal" in result.reason.lower()

    def test_aircraft_suppressed(self):
        governor = make_governor(make_card(relevant_objects=["Person", "Vehicle"]))
        detection = make_detection(object_class="Aircraft")
        result = governor.evaluate(detection, uav_battery_percent=80.0, communication_available=True)
        assert result.decision == "SUPPRESS"

    def test_relevant_object_not_suppressed(self):
        governor = make_governor(make_card(relevant_objects=["Person"]))
        detection = make_detection(object_class="Person")
        result = governor.evaluate(detection, uav_battery_percent=80.0, communication_available=True)
        assert result.decision != "SUPPRESS"

    def test_case_insensitive_relevance_check(self):
        governor = make_governor(make_card(relevant_objects=["person"]))
        detection = make_detection(object_class="Person")
        result = governor.evaluate(detection, uav_battery_percent=80.0, communication_available=True)
        # Should be relevant regardless of case
        assert result.evaluated_conditions.relevant_object is True


# ─────────────────────────────────────────────
#  Rule 4: Confidence Too Low → RETAIN
# ─────────────────────────────────────────────

class TestRule4LowConfidence:
    def test_confidence_below_threshold_returns_retain(self):
        governor = make_governor(make_card(min_confidence=60.0))
        detection = make_detection(confidence=45.0)
        result = governor.evaluate(detection, uav_battery_percent=80.0, communication_available=True)
        assert result.decision == "RETAIN"
        assert "confidence" in result.reason.lower()

    def test_confidence_at_threshold_passes(self):
        governor = make_governor(make_card(min_confidence=60.0))
        detection = make_detection(confidence=60.0)
        result = governor.evaluate(detection, uav_battery_percent=80.0, communication_available=True)
        assert result.evaluated_conditions.confidence_satisfied is True

    def test_confidence_above_threshold_passes(self):
        governor = make_governor(make_card(min_confidence=60.0))
        detection = make_detection(confidence=90.0)
        result = governor.evaluate(detection, uav_battery_percent=80.0, communication_available=True)
        assert result.evaluated_conditions.confidence_satisfied is True


# ─────────────────────────────────────────────
#  Rule 5: Outside Priority Zone → RETAIN
# ─────────────────────────────────────────────

class TestRule5OutsideZone:
    def test_target_outside_zone_returns_retain(self):
        governor = make_governor(make_card())
        detection = make_detection(lat=OUTSIDE_LAT, lng=OUTSIDE_LNG)
        result = governor.evaluate(detection, uav_battery_percent=80.0, communication_available=True)
        assert result.decision == "RETAIN"
        assert result.evaluated_conditions.inside_priority_zone is False

    def test_reason_mentions_outside_zone(self):
        governor = make_governor(make_card())
        detection = make_detection(lat=OUTSIDE_LAT, lng=OUTSIDE_LNG)
        result = governor.evaluate(detection, uav_battery_percent=80.0, communication_available=True)
        assert "outside" in result.reason.lower() or "zone" in result.reason.lower()

    def test_target_inside_zone_passes(self):
        governor = make_governor(make_card())
        detection = make_detection(lat=INSIDE_LAT, lng=INSIDE_LNG)
        result = governor.evaluate(detection, uav_battery_percent=80.0, communication_available=True)
        assert result.evaluated_conditions.inside_priority_zone is True


# ─────────────────────────────────────────────
#  Rule 6: Persistence Not Satisfied → RETAIN
# ─────────────────────────────────────────────

class TestRule6PersistenceNotMet:
    def test_persistence_below_threshold_returns_retain(self):
        governor = make_governor(make_card(persistence_frames=3))
        detection = make_detection(lat=INSIDE_LAT, lng=INSIDE_LNG, persistence=2)
        result = governor.evaluate(detection, uav_battery_percent=80.0, communication_available=True)
        assert result.decision == "RETAIN"
        assert result.evaluated_conditions.persistence_satisfied is False

    def test_persistence_exactly_at_threshold_passes(self):
        governor = make_governor(make_card(persistence_frames=3))
        detection = make_detection(lat=INSIDE_LAT, lng=INSIDE_LNG, persistence=3)
        result = governor.evaluate(detection, uav_battery_percent=80.0, communication_available=True)
        assert result.evaluated_conditions.persistence_satisfied is True

    def test_persistence_above_threshold_passes(self):
        governor = make_governor(make_card(persistence_frames=2))
        detection = make_detection(lat=INSIDE_LAT, lng=INSIDE_LNG, persistence=5)
        result = governor.evaluate(detection, uav_battery_percent=80.0, communication_available=True)
        assert result.evaluated_conditions.persistence_satisfied is True

    def test_persistence_one_frame_short_returns_retain(self):
        governor = make_governor(make_card(persistence_frames=5))
        detection = make_detection(lat=INSIDE_LAT, lng=INSIDE_LNG, persistence=4)
        result = governor.evaluate(detection, uav_battery_percent=80.0, communication_available=True)
        assert result.decision == "RETAIN"


# ─────────────────────────────────────────────
#  Rule 7: Evidence Required → EVIDENCE
# ─────────────────────────────────────────────

class TestRule7EvidenceRequired:
    def test_evidence_enabled_returns_evidence(self):
        governor = make_governor(make_card(evidence="Enabled"))
        detection = make_detection(lat=INSIDE_LAT, lng=INSIDE_LNG, persistence=3)
        result = governor.evaluate(detection, uav_battery_percent=80.0, communication_available=True)
        assert result.decision == "EVIDENCE"
        assert result.evaluated_conditions.evidence_required is True

    def test_evidence_decision_contains_reason(self):
        governor = make_governor(make_card(evidence="Enabled"))
        detection = make_detection(lat=INSIDE_LAT, lng=INSIDE_LNG, persistence=3)
        result = governor.evaluate(detection, uav_battery_percent=80.0, communication_available=True)
        assert len(result.reason) > 10
        assert "evidence" in result.action.lower() or "capture" in result.action.lower()


# ─────────────────────────────────────────────
#  Rule 8: All Conditions Met → EVENT
# ─────────────────────────────────────────────

class TestRule8EventTransmit:
    def test_all_conditions_satisfied_returns_event(self):
        governor = make_governor(make_card(evidence="Disabled"))
        detection = make_detection(
            object_class="Person",
            confidence=90.0,
            lat=INSIDE_LAT,
            lng=INSIDE_LNG,
            persistence=3,
        )
        result = governor.evaluate(detection, uav_battery_percent=80.0, communication_available=True)
        assert result.decision == "EVENT"

    def test_event_contains_mission_id(self):
        governor = make_governor(make_card())
        detection = make_detection(lat=INSIDE_LAT, lng=INSIDE_LNG)
        result = governor.evaluate(detection, uav_battery_percent=80.0, communication_available=True)
        assert result.mission_id == "TEST-M01"

    def test_event_contains_zone_name(self):
        governor = make_governor(make_card())
        detection = make_detection(lat=INSIDE_LAT, lng=INSIDE_LNG)
        result = governor.evaluate(detection, uav_battery_percent=80.0, communication_available=True)
        assert result.zone_name == "Zone Alpha"

    def test_event_evaluated_conditions_all_true(self):
        governor = make_governor(make_card())
        detection = make_detection(lat=INSIDE_LAT, lng=INSIDE_LNG)
        result = governor.evaluate(detection, uav_battery_percent=80.0, communication_available=True)
        conds = result.evaluated_conditions
        assert conds.communication_available is True
        assert conds.battery_above_threshold is True
        assert conds.relevant_object is True
        assert conds.confidence_satisfied is True
        assert conds.inside_priority_zone is True
        assert conds.persistence_satisfied is True
        assert conds.evidence_required is False

    def test_vehicle_detection_produces_event(self):
        governor = make_governor(make_card(relevant_objects=["Vehicle"]))
        detection = make_detection(
            object_class="Vehicle",
            confidence=75.0,
            lat=INSIDE_LAT,
            lng=INSIDE_LNG,
            persistence=2,
        )
        result = governor.evaluate(detection, uav_battery_percent=60.0, communication_available=True)
        assert result.decision == "EVENT"

    def test_target_type_preserved_in_decision(self):
        governor = make_governor(make_card())
        detection = make_detection(object_class="Person", lat=INSIDE_LAT, lng=INSIDE_LNG)
        result = governor.evaluate(detection, uav_battery_percent=80.0, communication_available=True)
        assert result.target_type == "Person"


# ─────────────────────────────────────────────
#  Decision Priority Order Tests
# ─────────────────────────────────────────────

class TestDecisionPriorityOrder:
    def test_comm_down_beats_battery_low(self):
        """Rule 1 (comm) takes precedence over Rule 2 (battery)."""
        governor = make_governor(make_card(battery_rth_percent=20.0))
        detection = make_detection()
        result = governor.evaluate(
            detection, uav_battery_percent=10.0, communication_available=False
        )
        assert result.decision == "RETAIN"
        # Must be specifically triggered by comm, not battery
        assert result.evaluated_conditions.communication_available is False

    def test_battery_low_beats_irrelevant_object(self):
        """Rule 2 (battery) takes precedence over Rule 3 (relevance)."""
        governor = make_governor(make_card(battery_rth_percent=20.0, relevant_objects=["Person"]))
        detection = make_detection(object_class="Animal")
        result = governor.evaluate(
            detection, uav_battery_percent=15.0, communication_available=True
        )
        assert result.decision == "RETAIN"
        # Rule 2 fired first; relevant_object would be False but battery check came first
        assert result.evaluated_conditions.battery_above_threshold is False

    def test_suppress_before_confidence(self):
        """Rule 3 (suppress) takes precedence over Rule 4 (confidence)."""
        governor = make_governor(make_card(min_confidence=60.0, relevant_objects=["Person"]))
        detection = make_detection(object_class="Animal", confidence=10.0)
        result = governor.evaluate(
            detection, uav_battery_percent=80.0, communication_available=True
        )
        assert result.decision == "SUPPRESS"
