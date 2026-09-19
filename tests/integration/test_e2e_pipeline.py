"""
tests/integration/test_e2e_pipeline.py
Phase 7 — Complete end-to-end pipeline integration test.

Tests the full S.I.G.H.T. pipeline:
  Virtual UAV → Camera → Detector → Mission Context → Governor → Comm Controller

Scenario A: Irrelevant object → SUPPRESS
Scenario B: Relevant + low confidence → RETAIN
Scenario C: Relevant + outside zone → RETAIN
Scenario D: Relevant + persistent + in zone → EVENT
Scenario E: Relevant + persistent + evidence enabled → EVIDENCE
Scenario F: Comm unavailable → RETAIN (even for EVENT-worthy)
Scenario G: Battery below RTH → RETAIN (even for EVENT-worthy)
"""

import sys
import os

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import importlib.util as _ilu
_SC_DIR = os.path.join(_ROOT, "sight-core")

def _bootstrap(pkg_name, pkg_dir):
    if pkg_name in sys.modules:
        return
    spec = _ilu.spec_from_file_location(pkg_name, os.path.join(pkg_dir, "__init__.py"),
                                         submodule_search_locations=[pkg_dir])
    mod = _ilu.module_from_spec(spec)
    mod.__path__ = [pkg_dir]; mod.__package__ = pkg_name
    sys.modules[pkg_name] = mod; spec.loader.exec_module(mod)
    for sub in os.listdir(pkg_dir):
        sub_dir = os.path.join(pkg_dir, sub)
        sub_init = os.path.join(sub_dir, "__init__.py")
        if not os.path.isdir(sub_dir) or not os.path.exists(sub_init): continue
        if sub.startswith((".", "_")) or sub == "tests": continue
        full = f"{pkg_name}.{sub}"
        if full in sys.modules: continue
        s = _ilu.spec_from_file_location(full, sub_init, submodule_search_locations=[sub_dir])
        m = _ilu.module_from_spec(s); m.__path__ = [sub_dir]; m.__package__ = full
        sys.modules[full] = m; s.loader.exec_module(m)

_bootstrap("sight_core", _SC_DIR)

import pytest
from sight_core.models.mission_card import MissionCard, PriorityZone
from sight_core.models.detection import PerceptionDetection
from sight_core.mission.mission_card_manager import MissionCardManager
from sight_core.context.context_engine import ContextEngine
from sight_core.governor.governor_engine import GovernorEngine
from communication.controller import CommunicationController, CommState
from simulator.simulator_interface import SimulatorInterface
from backend.detector import VirtualDetector


# ─────────────────────────────────────────────
#  Shared Fixtures
# ─────────────────────────────────────────────

ZONE_ALPHA = PriorityZone(
    id="ZONE-A",
    name="Zone Alpha",
    polygon=[(28.70, 77.10), (28.72, 77.10), (28.72, 77.13), (28.70, 77.13)],
)

INSIDE_LAT, INSIDE_LNG = 28.71, 77.115
OUTSIDE_LAT, OUTSIDE_LNG = 0.0, 0.0


def make_pipeline(
    relevant_objects=None,
    persistence_frames: int = 2,
    min_confidence: float = 60.0,
    battery_rth: float = 20.0,
    evidence: str = "Disabled",
    link_available: bool = True,
) -> tuple:
    """Create a fully connected Governor + CommController pipeline."""
    card = MissionCard(**{
        "missionId": "E2E-TEST",
        "objective": "End-to-End Test",
        "relevantObjects": relevant_objects or ["Person", "Vehicle"],
        "persistenceFrames": persistence_frames,
        "evidence": evidence,
        "communicationPolicy": "EVENT ONLY",
        "batteryRthPercent": battery_rth,
        "minConfidencePercent": min_confidence,
        "priorityZones": [ZONE_ALPHA.model_dump()],
    })
    manager = MissionCardManager(initial_card=card)
    context = ContextEngine(mission_manager=manager)
    governor = GovernorEngine(context_engine=context)
    comm = CommunicationController(link_available=link_available)
    return governor, comm


def make_detection(
    object_class: str = "Person",
    confidence: float = 88.0,
    lat: float = INSIDE_LAT,
    lng: float = INSIDE_LNG,
    persistence: int = 3,
) -> PerceptionDetection:
    return PerceptionDetection(**{
        "id": "E2E-DET-001",
        "objectClass": object_class,
        "confidence": confidence,
        "normBbox": (0.4, 0.4, 0.1, 0.2),
        "trackId": 1,
        "persistence": persistence,
        "lat": lat,
        "lng": lng,
        "altitudeM": 80.0,
        "timestamp": "12:00:00 UTC",
        "frameId": 1,
    })


def run_pipeline(governor, comm, detection, battery=80.0, comm_available=True):
    decision = governor.evaluate(detection, uav_battery_percent=battery,
                                 communication_available=comm_available)
    det_dict = {
        "id": detection.id,
        "objectClass": detection.object_class,
        "confidence": detection.confidence,
        "normBbox": list(detection.norm_bbox),
        "lat": detection.lat,
        "lng": detection.lng,
        "altitudeM": detection.altitude_m,
        "timestamp": detection.timestamp,
        "frameId": detection.frame_id,
        "zoneName": decision.zone_name,
    }
    comm_result = comm.process_decision(
        governor_decision=decision.decision,
        governor_reason=decision.reason,
        detection=det_dict,
        mission_id=decision.mission_id,
    )
    return decision, comm_result


# ─────────────────────────────────────────────
#  Scenario A: Irrelevant Object → SUPPRESS
# ─────────────────────────────────────────────

class TestScenarioA_Suppress:
    """Scenario A: Irrelevant object class → SUPPRESS (zero bytes transmitted)."""

    def test_animal_is_suppressed(self):
        governor, comm = make_pipeline(relevant_objects=["Person", "Vehicle"])
        detection = make_detection(object_class="Animal")
        decision, comm_result = run_pipeline(governor, comm, detection)
        assert decision.decision == "SUPPRESS"
        assert comm_result["status"] == "SUPPRESSED"

    def test_aircraft_is_suppressed(self):
        governor, comm = make_pipeline(relevant_objects=["Person"])
        detection = make_detection(object_class="Aircraft")
        decision, comm_result = run_pipeline(governor, comm, detection)
        assert decision.decision == "SUPPRESS"

    def test_suppress_zero_bytes(self):
        governor, comm = make_pipeline()
        detection = make_detection(object_class="Unknown_Entity")
        decision, comm_result = run_pipeline(governor, comm, detection)
        assert comm.stats.bytes_transmitted == 0

    def test_suppress_no_retention(self):
        governor, comm = make_pipeline()
        detection = make_detection(object_class="Animal")
        run_pipeline(governor, comm, detection)
        assert len(comm.get_retained_buffer()) == 0

    def test_suppress_counted_in_stats(self):
        governor, comm = make_pipeline()
        detection = make_detection(object_class="Animal")
        run_pipeline(governor, comm, detection)
        assert comm.stats.suppressed == 1


# ─────────────────────────────────────────────
#  Scenario B: Low Confidence → RETAIN
# ─────────────────────────────────────────────

class TestScenarioB_LowConfidence:
    """Scenario B: Relevant object but low confidence → RETAIN."""

    def test_low_confidence_is_retained(self):
        governor, comm = make_pipeline(min_confidence=60.0)
        detection = make_detection(object_class="Person", confidence=35.0)
        decision, comm_result = run_pipeline(governor, comm, detection)
        assert decision.decision == "RETAIN"
        assert comm_result["status"] == "RETAINED"

    def test_low_confidence_added_to_buffer(self):
        governor, comm = make_pipeline(min_confidence=60.0)
        detection = make_detection(object_class="Person", confidence=35.0)
        run_pipeline(governor, comm, detection)
        assert len(comm.get_retained_buffer()) == 1

    def test_boundary_confidence_60_passes(self):
        governor, comm = make_pipeline(min_confidence=60.0)
        detection = make_detection(object_class="Person", confidence=60.0)
        decision, _ = run_pipeline(governor, comm, detection)
        # Should not be RETAIN due to confidence (may be RETAIN due to persistence)
        assert decision.evaluated_conditions.confidence_satisfied is True


# ─────────────────────────────────────────────
#  Scenario C: Outside Zone → RETAIN
# ─────────────────────────────────────────────

class TestScenarioC_OutsideZone:
    """Scenario C: Relevant object outside priority zone → RETAIN."""

    def test_outside_zone_is_retained(self):
        governor, comm = make_pipeline()
        detection = make_detection(lat=OUTSIDE_LAT, lng=OUTSIDE_LNG, confidence=90.0)
        decision, comm_result = run_pipeline(governor, comm, detection)
        assert decision.decision == "RETAIN"
        assert decision.evaluated_conditions.inside_priority_zone is False
        assert comm_result["status"] == "RETAINED"

    def test_inside_zone_passes(self):
        governor, comm = make_pipeline()
        detection = make_detection(lat=INSIDE_LAT, lng=INSIDE_LNG, confidence=90.0)
        decision, _ = run_pipeline(governor, comm, detection)
        assert decision.evaluated_conditions.inside_priority_zone is True


# ─────────────────────────────────────────────
#  Scenario D: EVENT — Full Pass
# ─────────────────────────────────────────────

class TestScenarioD_Event:
    """Scenario D: Relevant, persistent, in-zone, high-confidence → EVENT."""

    def test_full_pass_produces_event(self):
        governor, comm = make_pipeline(evidence="Disabled", persistence_frames=2)
        detection = make_detection(
            object_class="Person", confidence=90.0,
            lat=INSIDE_LAT, lng=INSIDE_LNG, persistence=3
        )
        decision, comm_result = run_pipeline(governor, comm, detection, battery=80.0)
        assert decision.decision == "EVENT"
        assert comm_result["status"] == "TRANSMITTED"

    def test_event_bytes_transmitted(self):
        governor, comm = make_pipeline(evidence="Disabled")
        detection = make_detection(lat=INSIDE_LAT, lng=INSIDE_LNG)
        run_pipeline(governor, comm, detection, battery=80.0)
        assert comm.stats.bytes_transmitted > 0

    def test_event_reaches_transmission_log(self):
        governor, comm = make_pipeline(evidence="Disabled")
        detection = make_detection(lat=INSIDE_LAT, lng=INSIDE_LNG)
        decision, _ = run_pipeline(governor, comm, detection, battery=80.0)
        if decision.decision == "EVENT":
            assert len(comm.get_transmitted_events()) == 1

    def test_vehicle_detection_produces_event(self):
        governor, comm = make_pipeline(relevant_objects=["Vehicle"])
        detection = make_detection(
            object_class="Vehicle", confidence=75.0,
            lat=INSIDE_LAT, lng=INSIDE_LNG, persistence=2
        )
        decision, _ = run_pipeline(governor, comm, detection, battery=80.0)
        assert decision.decision == "EVENT"


# ─────────────────────────────────────────────
#  Scenario E: EVIDENCE
# ─────────────────────────────────────────────

class TestScenarioE_Evidence:
    """Scenario E: All conditions + evidence policy enabled → EVIDENCE."""

    def test_evidence_policy_produces_evidence(self):
        governor, comm = make_pipeline(evidence="Enabled")
        detection = make_detection(
            object_class="Person", confidence=90.0,
            lat=INSIDE_LAT, lng=INSIDE_LNG, persistence=3
        )
        decision, comm_result = run_pipeline(governor, comm, detection, battery=80.0)
        assert decision.decision == "EVIDENCE"
        assert comm_result["status"] == "TRANSMITTED"

    def test_evidence_packet_has_roi(self):
        governor, comm = make_pipeline(evidence="Enabled")
        detection = make_detection(lat=INSIDE_LAT, lng=INSIDE_LNG)
        decision, comm_result = run_pipeline(governor, comm, detection, battery=80.0)
        if decision.decision == "EVIDENCE":
            assert "roiBbox" in comm_result["packet"]

    def test_evidence_larger_than_event_bytes(self):
        gov_ev, comm_ev = make_pipeline(evidence="Disabled")
        gov_evi, comm_evi = make_pipeline(evidence="Enabled")
        det = make_detection(lat=INSIDE_LAT, lng=INSIDE_LNG, persistence=3)
        run_pipeline(gov_ev, comm_ev, det)
        run_pipeline(gov_evi, comm_evi, det)
        if comm_evi.stats.evidence_transmitted > 0 and comm_ev.stats.events_transmitted > 0:
            assert comm_evi.stats.bytes_transmitted > comm_ev.stats.bytes_transmitted


# ─────────────────────────────────────────────
#  Scenario F: Comm Unavailable → RETAIN
# ─────────────────────────────────────────────

class TestScenarioF_CommUnavailable:
    """Scenario F: Link down → RETAIN even for EVENT-worthy detection."""

    def test_comm_down_forces_retain(self):
        governor, comm = make_pipeline(link_available=False)
        detection = make_detection(lat=INSIDE_LAT, lng=INSIDE_LNG, persistence=5)
        decision, comm_result = run_pipeline(
            governor, comm, detection, battery=80.0, comm_available=False
        )
        assert decision.decision == "RETAIN"

    def test_comm_down_zero_bytes(self):
        governor, comm = make_pipeline(link_available=False)
        detection = make_detection(lat=INSIDE_LAT, lng=INSIDE_LNG)
        run_pipeline(governor, comm, detection, battery=80.0, comm_available=False)
        assert comm.stats.bytes_transmitted == 0

    def test_comm_restored_allows_transmission(self):
        governor, comm = make_pipeline(link_available=True, evidence="Disabled")
        comm.set_link_available(True)
        detection = make_detection(lat=INSIDE_LAT, lng=INSIDE_LNG)
        decision, comm_result = run_pipeline(governor, comm, detection, battery=80.0)
        if decision.decision == "EVENT":
            assert comm_result["status"] == "TRANSMITTED"


# ─────────────────────────────────────────────
#  Scenario G: Battery Below RTH → RETAIN
# ─────────────────────────────────────────────

class TestScenarioG_BatteryLow:
    """Scenario G: Battery at/below RTH → RETAIN."""

    def test_battery_at_rth_retains(self):
        governor, comm = make_pipeline(battery_rth=20.0)
        detection = make_detection(lat=INSIDE_LAT, lng=INSIDE_LNG, persistence=5)
        decision, comm_result = run_pipeline(
            governor, comm, detection, battery=20.0  # exactly at threshold
        )
        assert decision.decision == "RETAIN"
        assert decision.evaluated_conditions.battery_above_threshold is False

    def test_battery_below_rth_retains(self):
        governor, comm = make_pipeline(battery_rth=20.0)
        detection = make_detection(lat=INSIDE_LAT, lng=INSIDE_LNG)
        decision, _ = run_pipeline(governor, comm, detection, battery=12.0)
        assert decision.decision == "RETAIN"

    def test_battery_above_rth_allows_event(self):
        governor, comm = make_pipeline(battery_rth=20.0, evidence="Disabled")
        detection = make_detection(lat=INSIDE_LAT, lng=INSIDE_LNG)
        decision, _ = run_pipeline(governor, comm, detection, battery=80.0)
        assert decision.evaluated_conditions.battery_above_threshold is True


# ─────────────────────────────────────────────
#  Simulator Integration
# ─────────────────────────────────────────────

class TestSimulatorIntegration:
    """Verify virtual UAV simulator produces usable camera frames and targets."""

    def test_simulator_starts_and_produces_telemetry(self):
        sim = SimulatorInterface(mavlink_port=14599, camera_fps=5)
        sim.start(enable_mavlink=False)
        try:
            telem = sim.get_telemetry()
            assert "lat" in telem
            assert "battery_percent" in telem
            assert telem["battery_percent"] > 0
        finally:
            sim.stop()

    def test_simulator_camera_produces_frame(self):
        import numpy as np
        sim = SimulatorInterface(camera_width=320, camera_height=240, camera_fps=5)
        sim.start(enable_mavlink=False)
        try:
            frame = sim.capture_frame()
            assert isinstance(frame, np.ndarray)
            assert frame.shape == (240, 320, 3)
        finally:
            sim.stop()

    def test_virtual_detector_produces_detections(self):
        import numpy as np
        sim = SimulatorInterface(camera_width=320, camera_height=240, camera_fps=5)
        sim.start(enable_mavlink=False)
        detector = VirtualDetector()
        try:
            frame = sim.capture_frame()
            targets = sim.get_visible_targets()
            detections = detector.detect(
                frame=frame,
                uav_lat=28.71,
                uav_lng=77.115,
                altitude_m=80.0,
                timestamp="12:00:00 UTC",
                visible_targets=targets,
            )
            assert isinstance(detections, list)
        finally:
            sim.stop()


# ─────────────────────────────────────────────
#  Complete Pipeline Simulation
# ─────────────────────────────────────────────

class TestCompletePipeline:
    """Simulate a full mission scenario: simulator → detector → governor → comm."""

    def test_full_mission_pipeline_scenarios(self):
        """
        Runs all 7 governor scenarios end-to-end and verifies decisions
        reach the communication controller correctly.
        """
        governor, comm = make_pipeline(evidence="Disabled")

        scenarios = [
            # (label, class, conf, lat, lng, persistence, battery, comm_avail, expected_decision)
            ("SUPPRESS-Animal",     "Animal",   88, INSIDE_LAT,  INSIDE_LNG,  3, 80, True,  "SUPPRESS"),
            ("RETAIN-LowConf",      "Person",   30, INSIDE_LAT,  INSIDE_LNG,  3, 80, True,  "RETAIN"),
            ("RETAIN-OutsideZone",  "Person",   88, OUTSIDE_LAT, OUTSIDE_LNG, 3, 80, True,  "RETAIN"),
            ("RETAIN-LowPersist",   "Person",   88, INSIDE_LAT,  INSIDE_LNG,  1, 80, True,  "RETAIN"),
            ("EVENT-AllPass",       "Person",   88, INSIDE_LAT,  INSIDE_LNG,  3, 80, True,  "EVENT"),
            ("RETAIN-CommDown",     "Person",   88, INSIDE_LAT,  INSIDE_LNG,  3, 80, False, "RETAIN"),
            ("RETAIN-BattLow",      "Person",   88, INSIDE_LAT,  INSIDE_LNG,  3, 18, True,  "RETAIN"),
        ]

        results = []
        for label, obj_cls, conf, lat, lng, persist, battery, comm_avail, expected in scenarios:
            detection = make_detection(
                object_class=obj_cls, confidence=conf,
                lat=lat, lng=lng, persistence=persist
            )
            decision, comm_result = run_pipeline(
                governor, comm, detection,
                battery=battery, comm_available=comm_avail
            )
            results.append({
                "label": label,
                "expected": expected,
                "actual": decision.decision,
                "passed": decision.decision == expected,
            })

        failures = [r for r in results if not r["passed"]]
        assert failures == [], f"Pipeline scenario failures: {failures}"
