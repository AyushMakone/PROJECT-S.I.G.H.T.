"""
tests/communication/test_controller.py
Phase 5 — Communication Controller unit tests.
"""

import sys
import os

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

import pytest
from communication.controller import (
    CommunicationController, CommState, EventPacket, EvidencePacket
)

# ─────────────────────────────────────────────
#  Fixtures
# ─────────────────────────────────────────────

SAMPLE_DETECTION = {
    "id": "DET-001",
    "objectClass": "Person",
    "confidence": 88.0,
    "normBbox": [0.4, 0.4, 0.1, 0.2],
    "trackId": 1,
    "persistence": 3,
    "lat": 28.71,
    "lng": 77.115,
    "altitudeM": 80.0,
    "timestamp": "12:00:00 UTC",
    "frameId": 1,
    "zoneName": "Zone Alpha",
}

MISSION_ID = "TEST-M01"


def fresh_controller(**kwargs) -> CommunicationController:
    return CommunicationController(**kwargs)


# ─────────────────────────────────────────────
#  Initial State
# ─────────────────────────────────────────────

class TestInitialState:
    def test_initial_state_is_inactive(self):
        ctrl = fresh_controller()
        assert ctrl.state == CommState.INACTIVE

    def test_initial_stats_zero(self):
        ctrl = fresh_controller()
        s = ctrl.stats
        assert s.packets_sent == 0
        assert s.bytes_transmitted == 0
        assert s.events_transmitted == 0
        assert s.evidence_transmitted == 0
        assert s.suppressed == 0
        assert s.retained == 0

    def test_link_available_by_default(self):
        ctrl = fresh_controller()
        assert ctrl.link_available is True

    def test_retention_buffer_empty_initially(self):
        ctrl = fresh_controller()
        assert ctrl.get_retained_buffer() == []


# ─────────────────────────────────────────────
#  SUPPRESS
# ─────────────────────────────────────────────

class TestSuppress:
    def test_suppress_returns_suppressed_status(self):
        ctrl = fresh_controller()
        result = ctrl.process_decision("SUPPRESS", "Not relevant", SAMPLE_DETECTION, MISSION_ID)
        assert result["status"] == "SUPPRESSED"

    def test_suppress_zero_bytes(self):
        ctrl = fresh_controller()
        result = ctrl.process_decision("SUPPRESS", "Not relevant", SAMPLE_DETECTION, MISSION_ID)
        assert result["bytes_transmitted"] == 0

    def test_suppress_increments_suppressed_count(self):
        ctrl = fresh_controller()
        ctrl.process_decision("SUPPRESS", "Not relevant", SAMPLE_DETECTION, MISSION_ID)
        ctrl.process_decision("SUPPRESS", "Not relevant", SAMPLE_DETECTION, MISSION_ID)
        assert ctrl.stats.suppressed == 2

    def test_suppress_state_remains_inactive(self):
        ctrl = fresh_controller()
        ctrl.process_decision("SUPPRESS", "Not relevant", SAMPLE_DETECTION, MISSION_ID)
        assert ctrl.state == CommState.INACTIVE

    def test_suppress_no_packet_returned(self):
        ctrl = fresh_controller()
        result = ctrl.process_decision("SUPPRESS", "Not relevant", SAMPLE_DETECTION, MISSION_ID)
        assert result["packet"] is None


# ─────────────────────────────────────────────
#  RETAIN
# ─────────────────────────────────────────────

class TestRetain:
    def test_retain_returns_retained_status(self):
        ctrl = fresh_controller()
        result = ctrl.process_decision("RETAIN", "Low confidence", SAMPLE_DETECTION, MISSION_ID)
        assert result["status"] == "RETAINED"

    def test_retain_zero_bytes_transmitted(self):
        ctrl = fresh_controller()
        result = ctrl.process_decision("RETAIN", "Low confidence", SAMPLE_DETECTION, MISSION_ID)
        assert result["bytes_transmitted"] == 0

    def test_retain_adds_to_buffer(self):
        ctrl = fresh_controller()
        ctrl.process_decision("RETAIN", "Outside zone", SAMPLE_DETECTION, MISSION_ID)
        assert len(ctrl.get_retained_buffer()) == 1

    def test_retain_buffer_grows(self):
        ctrl = fresh_controller()
        ctrl.process_decision("RETAIN", "Reason A", SAMPLE_DETECTION, MISSION_ID)
        ctrl.process_decision("RETAIN", "Reason B", SAMPLE_DETECTION, MISSION_ID)
        assert len(ctrl.get_retained_buffer()) == 2

    def test_retain_state_stays_inactive(self):
        ctrl = fresh_controller()
        ctrl.process_decision("RETAIN", "Persistence", SAMPLE_DETECTION, MISSION_ID)
        assert ctrl.state == CommState.INACTIVE

    def test_retain_no_packet_returned(self):
        ctrl = fresh_controller()
        result = ctrl.process_decision("RETAIN", "Reason", SAMPLE_DETECTION, MISSION_ID)
        assert result["packet"] is None


# ─────────────────────────────────────────────
#  EVENT
# ─────────────────────────────────────────────

class TestEvent:
    def test_event_returns_transmitted_status(self):
        ctrl = fresh_controller(link_available=True)
        result = ctrl.process_decision("EVENT", "All conditions met", SAMPLE_DETECTION, MISSION_ID)
        assert result["status"] == "TRANSMITTED"

    def test_event_transmits_nonzero_bytes(self):
        ctrl = fresh_controller(link_available=True)
        result = ctrl.process_decision("EVENT", "All conditions met", SAMPLE_DETECTION, MISSION_ID)
        assert result["bytes_transmitted"] > 0

    def test_event_increments_packet_count(self):
        ctrl = fresh_controller(link_available=True)
        ctrl.process_decision("EVENT", "All met", SAMPLE_DETECTION, MISSION_ID)
        assert ctrl.stats.packets_sent == 1
        assert ctrl.stats.events_transmitted == 1

    def test_event_returns_to_inactive(self):
        ctrl = fresh_controller(link_available=True)
        ctrl.process_decision("EVENT", "All met", SAMPLE_DETECTION, MISSION_ID)
        assert ctrl.state == CommState.INACTIVE

    def test_event_packet_has_mission_id(self):
        ctrl = fresh_controller(link_available=True)
        result = ctrl.process_decision("EVENT", "All met", SAMPLE_DETECTION, MISSION_ID)
        assert result["packet"]["missionId"] == MISSION_ID

    def test_event_packet_type(self):
        ctrl = fresh_controller(link_available=True)
        result = ctrl.process_decision("EVENT", "All met", SAMPLE_DETECTION, MISSION_ID)
        assert result["packet"]["packetType"] == "EVENT_METADATA"

    def test_event_link_unavailable_retains(self):
        ctrl = fresh_controller(link_available=False)
        result = ctrl.process_decision("EVENT", "All met", SAMPLE_DETECTION, MISSION_ID)
        assert result["status"] == "LINK_UNAVAILABLE"
        assert result["bytes_transmitted"] == 0

    def test_event_latency_recorded(self):
        ctrl = fresh_controller(link_available=True, simulate_latency_ms=10.0)
        ctrl.process_decision("EVENT", "All met", SAMPLE_DETECTION, MISSION_ID)
        assert ctrl.stats.last_transmission_ms is not None
        assert ctrl.stats.last_transmission_ms >= 10.0

    def test_multiple_events_accumulate(self):
        ctrl = fresh_controller(link_available=True)
        for _ in range(3):
            ctrl.process_decision("EVENT", "All met", SAMPLE_DETECTION, MISSION_ID)
        assert ctrl.stats.events_transmitted == 3
        assert len(ctrl.get_transmitted_events()) == 3


# ─────────────────────────────────────────────
#  EVIDENCE
# ─────────────────────────────────────────────

class TestEvidence:
    def test_evidence_returns_transmitted_status(self):
        ctrl = fresh_controller(link_available=True)
        result = ctrl.process_decision("EVIDENCE", "Evidence required", SAMPLE_DETECTION, MISSION_ID)
        assert result["status"] == "TRANSMITTED"

    def test_evidence_larger_than_event(self):
        ctrl_ev = fresh_controller(link_available=True)
        ctrl_evi = fresh_controller(link_available=True)
        ev_result = ctrl_ev.process_decision("EVENT", "All met", SAMPLE_DETECTION, MISSION_ID)
        evi_result = ctrl_evi.process_decision("EVIDENCE", "Evidence req", SAMPLE_DETECTION, MISSION_ID)
        assert evi_result["bytes_transmitted"] > ev_result["bytes_transmitted"]

    def test_evidence_packet_type(self):
        ctrl = fresh_controller(link_available=True)
        result = ctrl.process_decision("EVIDENCE", "Evidence req", SAMPLE_DETECTION, MISSION_ID)
        assert result["packet"]["packetType"] == "EVIDENCE_METADATA"

    def test_evidence_contains_roi(self):
        ctrl = fresh_controller(link_available=True)
        result = ctrl.process_decision("EVIDENCE", "Evidence req", SAMPLE_DETECTION, MISSION_ID)
        assert "roiBbox" in result["packet"]
        assert "roiResolution" in result["packet"]

    def test_evidence_increments_evidence_count(self):
        ctrl = fresh_controller(link_available=True)
        ctrl.process_decision("EVIDENCE", "Evidence req", SAMPLE_DETECTION, MISSION_ID)
        assert ctrl.stats.evidence_transmitted == 1

    def test_evidence_link_unavailable_retains(self):
        ctrl = fresh_controller(link_available=False)
        result = ctrl.process_decision("EVIDENCE", "Evidence req", SAMPLE_DETECTION, MISSION_ID)
        assert result["status"] == "LINK_UNAVAILABLE"


# ─────────────────────────────────────────────
#  Mixed Scenario
# ─────────────────────────────────────────────

class TestMixedScenario:
    def test_mixed_decisions_tracked_correctly(self):
        ctrl = fresh_controller(link_available=True)
        ctrl.process_decision("SUPPRESS", "Irrelevant", SAMPLE_DETECTION, MISSION_ID)
        ctrl.process_decision("RETAIN", "Outside zone", SAMPLE_DETECTION, MISSION_ID)
        ctrl.process_decision("RETAIN", "Low persistence", SAMPLE_DETECTION, MISSION_ID)
        ctrl.process_decision("EVENT", "All met", SAMPLE_DETECTION, MISSION_ID)
        ctrl.process_decision("EVIDENCE", "Evidence req", SAMPLE_DETECTION, MISSION_ID)

        stats = ctrl.stats
        assert stats.suppressed == 1
        assert stats.retained == 2
        assert stats.events_transmitted == 1
        assert stats.evidence_transmitted == 1
        assert stats.total_processed == 5

    def test_total_bytes_from_transmissions_only(self):
        ctrl = fresh_controller(link_available=True)
        ctrl.process_decision("SUPPRESS", "Irrelevant", SAMPLE_DETECTION, MISSION_ID)
        ctrl.process_decision("RETAIN", "Outside zone", SAMPLE_DETECTION, MISSION_ID)
        ctrl.process_decision("EVENT", "All met", SAMPLE_DETECTION, MISSION_ID)
        # Only EVENT should contribute bytes
        assert ctrl.stats.bytes_transmitted > 0
        # SUPPRESS and RETAIN contribute 0


# ─────────────────────────────────────────────
#  Link Toggle
# ─────────────────────────────────────────────

class TestLinkToggle:
    def test_link_toggle_works(self):
        ctrl = fresh_controller()
        ctrl.set_link_available(False)
        assert ctrl.link_available is False
        ctrl.set_link_available(True)
        assert ctrl.link_available is True

    def test_reset_clears_all_state(self):
        ctrl = fresh_controller(link_available=True)
        ctrl.process_decision("EVENT", "All met", SAMPLE_DETECTION, MISSION_ID)
        ctrl.process_decision("RETAIN", "Outside", SAMPLE_DETECTION, MISSION_ID)
        ctrl.reset_stats()
        assert ctrl.stats.packets_sent == 0
        assert ctrl.stats.suppressed == 0
        assert ctrl.stats.retained == 0
        assert ctrl.get_transmitted_events() == []
        assert ctrl.get_retained_buffer() == []


# ─────────────────────────────────────────────
#  Packet Byte Size
# ─────────────────────────────────────────────

class TestPacketSize:
    def test_event_packet_byte_size_nonzero(self):
        pkt = EventPacket(
            packet_id="EVT-00001",
            mission_id="SIGHT-M01",
            target_type="Person",
            confidence=88.0,
            lat=28.71,
            lng=77.115,
            altitude_m=80.0,
            zone_name="Zone Alpha",
            timestamp="12:00:00 UTC",
        )
        assert pkt.byte_size() > 0

    def test_evidence_packet_larger_than_event_packet(self):
        evt = EventPacket(
            packet_id="EVT-00001", mission_id="M1", target_type="Person",
            confidence=88.0, lat=28.71, lng=77.1, altitude_m=80.0,
            zone_name="Zone A", timestamp="12:00:00 UTC"
        )
        evi = EvidencePacket(
            packet_id="EVI-00001", mission_id="M1", target_type="Person",
            confidence=88.0, lat=28.71, lng=77.1, altitude_m=80.0,
            zone_name="Zone A", timestamp="12:00:00 UTC",
            roi_bbox=(0.4, 0.4, 0.1, 0.2), roi_resolution=(640, 480), frame_id=1
        )
        assert evi.byte_size() > evt.byte_size()
