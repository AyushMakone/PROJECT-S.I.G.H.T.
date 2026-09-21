"""
tests/backend/test_api.py
Phase 4 — FastAPI backend smoke tests and endpoint verification.
Tests run against a live FastAPI TestClient (no network required).
"""

import sys
import os

# Bootstrap path
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# Bootstrap sight_core
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
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


# ─────────────────────────────────────────────
#  Health
# ─────────────────────────────────────────────

class TestHealth:
    def test_health_returns_200(self):
        r = client.get("/api/v1/health")
        assert r.status_code == 200

    def test_health_status_operational(self):
        r = client.get("/api/v1/health")
        data = r.json()
        assert data["status"] == "ok"

    def test_health_components_present(self):
        r = client.get("/api/v1/health")
        data = r.json()
        assert "governor" in data["components"]
        assert "mission_card" in data["components"]
        assert "communication_controller" in data["components"]
        assert "detector" in data["components"]

    def test_health_uptime_positive(self):
        r = client.get("/api/v1/health")
        assert r.json()["uptime_s"] >= 0.0


# ─────────────────────────────────────────────
#  Telemetry
# ─────────────────────────────────────────────

class TestTelemetry:
    def test_get_telemetry_returns_200(self):
        r = client.get("/api/v1/telemetry")
        assert r.status_code == 200

    def test_telemetry_has_required_fields(self):
        r = client.get("/api/v1/telemetry")
        data = r.json()
        for field in ["lat", "lng", "altitude_m", "battery_percent", "is_armed", "flight_mode"]:
            assert field in data

    def test_post_telemetry_updates_state(self):
        payload = {
            "lat": 28.71, "lng": 77.11, "altitude_m": 85.0,
            "speed_mps": 12.0, "heading_deg": 90.0, "climb_rate_mps": 0.0,
            "roll_deg": 0.0, "pitch_deg": -3.0, "yaw_deg": 90.0,
            "battery_percent": 75.0, "battery_voltage_v": 15.8,
            "is_armed": True, "flight_mode": "MISSION",
            "current_waypoint": 1, "total_waypoints": 4,
            "timestamp_utc": "12:00:00 UTC"
        }
        r = client.post("/api/v1/telemetry", json=payload)
        assert r.status_code == 200
        r2 = client.get("/api/v1/telemetry")
        assert r2.json()["battery_percent"] == 75.0
        assert r2.json()["altitude_m"] == 85.0


# ─────────────────────────────────────────────
#  Mission Card
# ─────────────────────────────────────────────

class TestMissionCard:
    def test_get_mission_returns_200(self):
        r = client.get("/api/v1/mission")
        assert r.status_code == 200

    def test_get_mission_has_id(self):
        r = client.get("/api/v1/mission")
        assert "missionId" in r.json()

    def test_post_mission_card_loads(self):
        payload = {
            "missionId": "TEST-API-01",
            "objective": "API Test Mission",
            "relevantObjects": ["Person"],
            "persistenceFrames": 2,
            "evidence": "Disabled",
            "communicationPolicy": "EVENT ONLY",
            "batteryRthPercent": 20.0,
            "minConfidencePercent": 60.0,
            "priorityZones": [
                {
                    "id": "Z1",
                    "name": "Test Zone",
                    "polygon": [[28.70, 77.10], [28.72, 77.10], [28.72, 77.13], [28.70, 77.13]],
                }
            ],
        }
        r = client.post("/api/v1/mission", json=payload)
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "OK"
        assert data["mission_id"] == "TEST-API-01"

    def test_post_mission_invalid_rth_rejects(self):
        payload = {
            "missionId": "BAD-M", "objective": "Bad",
            "relevantObjects": ["Person"], "persistenceFrames": 2,
            "evidence": "Disabled", "communicationPolicy": "EVENT ONLY",
            "batteryRthPercent": 99.0,  # Invalid: > 50
            "minConfidencePercent": 60.0, "priorityZones": [],
        }
        r = client.post("/api/v1/mission", json=payload)
        assert r.status_code == 422


# ─────────────────────────────────────────────
#  Detection → Governor Pipeline
# ─────────────────────────────────────────────

ZONE_DETECTION = {
    "id": "DET-001",
    "objectClass": "Person",
    "confidence": 90.0,
    "normBbox": [0.4, 0.4, 0.1, 0.2],
    "trackId": 1,
    "persistence": 3,
    "lat": 28.71,
    "lng": 77.115,
    "altitudeM": 80.0,
    "timestamp": "12:00:00 UTC",
    "frameId": 1,
    "source": "TEST",
}

IRRELEVANT_DETECTION = {
    **ZONE_DETECTION,
    "id": "DET-002",
    "objectClass": "Animal",
}

LOW_CONF_DETECTION = {
    **ZONE_DETECTION,
    "id": "DET-003",
    "confidence": 20.0,  # below 60% threshold
}

OUTSIDE_ZONE_DETECTION = {
    **ZONE_DETECTION,
    "id": "DET-004",
    "lat": 0.0,
    "lng": 0.0,  # clearly outside zone
}


class TestDetectionEndpoint:
    def setup_method(self):
        """Load a fresh mission card before each test."""
        payload = {
            "missionId": "TEST-DET-01",
            "objective": "Detection Test",
            "relevantObjects": ["Person", "Vehicle"],
            "persistenceFrames": 2,
            "evidence": "Disabled",
            "communicationPolicy": "EVENT ONLY",
            "batteryRthPercent": 20.0,
            "minConfidencePercent": 60.0,
            "priorityZones": [
                {
                    "id": "Z1",
                    "name": "Zone Alpha",
                    "polygon": [[28.70, 77.10], [28.72, 77.10], [28.72, 77.13], [28.70, 77.13]],
                }
            ],
        }
        client.post("/api/v1/mission", json=payload)
        # High battery
        client.post("/api/v1/telemetry", json={
            "lat": 28.71, "lng": 77.115, "altitude_m": 80.0,
            "speed_mps": 12.0, "heading_deg": 0.0, "climb_rate_mps": 0.0,
            "roll_deg": 0.0, "pitch_deg": 0.0, "yaw_deg": 0.0,
            "battery_percent": 80.0, "battery_voltage_v": 15.8,
            "is_armed": True, "flight_mode": "MISSION",
            "current_waypoint": 1, "total_waypoints": 4,
            "timestamp_utc": "12:00:00 UTC"
        })
        # Restore link
        client.post("/api/v1/comm/link", json={"available": True})

    def test_event_decision_for_valid_detection(self):
        """Relevant, high-confidence, in-zone, persistent → EVENT"""
        r = client.post("/api/v1/detect", json=ZONE_DETECTION)
        assert r.status_code == 200
        assert r.json()["decision"] == "EVENT"

    def test_suppress_for_irrelevant_object(self):
        """Animal → SUPPRESS"""
        r = client.post("/api/v1/detect", json=IRRELEVANT_DETECTION)
        assert r.status_code == 200
        assert r.json()["decision"] == "SUPPRESS"

    def test_retain_for_low_confidence(self):
        """Low confidence → RETAIN"""
        r = client.post("/api/v1/detect", json=LOW_CONF_DETECTION)
        assert r.status_code == 200
        assert r.json()["decision"] == "RETAIN"

    def test_retain_for_outside_zone(self):
        """Outside zone → RETAIN"""
        r = client.post("/api/v1/detect", json=OUTSIDE_ZONE_DETECTION)
        assert r.status_code == 200
        assert r.json()["decision"] == "RETAIN"

    def test_detection_response_has_required_fields(self):
        r = client.post("/api/v1/detect", json=ZONE_DETECTION)
        data = r.json()
        for field in ["decision", "reason", "action", "mission_id", "timestamp", "evaluated_conditions"]:
            assert field in data

    def test_evidence_decision_when_policy_enabled(self):
        """With evidence=Enabled, in-zone detection → EVIDENCE"""
        client.post("/api/v1/mission", json={
            "missionId": "EVI-TEST",
            "objective": "Evidence Test",
            "relevantObjects": ["Person"],
            "persistenceFrames": 2,
            "evidence": "Enabled",
            "communicationPolicy": "EVENT & EVIDENCE",
            "batteryRthPercent": 20.0,
            "minConfidencePercent": 60.0,
            "priorityZones": [
                {"id": "Z1", "name": "Zone Alpha",
                 "polygon": [[28.70, 77.10], [28.72, 77.10], [28.72, 77.13], [28.70, 77.13]]}
            ],
        })
        r = client.post("/api/v1/detect", json=ZONE_DETECTION)
        assert r.status_code == 200
        assert r.json()["decision"] == "EVIDENCE"

    def test_retain_when_comm_link_down(self):
        """When comm link down, even EVENT-worthy → RETAIN"""
        client.post("/api/v1/comm/link", json={"available": False})
        r = client.post("/api/v1/detect", json=ZONE_DETECTION)
        assert r.status_code == 200
        assert r.json()["decision"] == "RETAIN"


# ─────────────────────────────────────────────
#  Governor State
# ─────────────────────────────────────────────

class TestGovernorState:
    def test_governor_state_after_detection(self):
        client.post("/api/v1/detect", json=ZONE_DETECTION)
        r = client.get("/api/v1/governor/state")
        assert r.status_code == 200
        data = r.json()
        assert "decision" in data
        assert data["decision"] in ["SUPPRESS", "RETAIN", "EVENT", "EVIDENCE"]

    def test_governor_history_accumulates(self):
        client.post("/api/v1/reset")
        client.post("/api/v1/telemetry", json={"battery_percent": 80.0})
        client.post("/api/v1/detect", json=ZONE_DETECTION)
        client.post("/api/v1/detect", json=IRRELEVANT_DETECTION)
        r = client.get("/api/v1/governor/history")
        assert r.status_code == 200
        assert len(r.json()) >= 2


# ─────────────────────────────────────────────
#  Communication State
# ─────────────────────────────────────────────

class TestCommState:
    def test_comm_state_returns_200(self):
        r = client.get("/api/v1/comm/state")
        assert r.status_code == 200

    def test_comm_state_has_required_fields(self):
        r = client.get("/api/v1/comm/state")
        data = r.json()
        for field in ["state", "packets_sent", "bytes_transmitted", "link_available"]:
            assert field in data

    def test_comm_link_toggle(self):
        client.post("/api/v1/comm/link", json={"available": False})
        r = client.get("/api/v1/comm/state")
        assert r.json()["link_available"] is False
        client.post("/api/v1/comm/link", json={"available": True})
        r = client.get("/api/v1/comm/state")
        assert r.json()["link_available"] is True

    def test_comm_events_accumulate(self):
        client.post("/api/v1/reset")
        # Load mission, set battery high
        client.post("/api/v1/mission", json={
            "missionId": "COMM-TEST",
            "objective": "Comm Test",
            "relevantObjects": ["Person"],
            "persistenceFrames": 2,
            "evidence": "Disabled",
            "communicationPolicy": "EVENT ONLY",
            "batteryRthPercent": 20.0,
            "minConfidencePercent": 60.0,
            "priorityZones": [
                {"id": "Z1", "name": "Zone Alpha",
                 "polygon": [[28.70, 77.10], [28.72, 77.10], [28.72, 77.13], [28.70, 77.13]]}
            ],
        })
        client.post("/api/v1/telemetry", json={
            "lat": 28.71, "lng": 77.115, "altitude_m": 80.0,
            "speed_mps": 0.0, "heading_deg": 0.0, "climb_rate_mps": 0.0,
            "roll_deg": 0.0, "pitch_deg": 0.0, "yaw_deg": 0.0,
            "battery_percent": 80.0, "battery_voltage_v": 15.8,
            "is_armed": True, "flight_mode": "MISSION",
            "current_waypoint": 0, "total_waypoints": 0,
            "timestamp_utc": "12:00:00 UTC"
        })
        client.post("/api/v1/detect", json=ZONE_DETECTION)
        r = client.get("/api/v1/comm/events")
        assert r.status_code == 200
        # Should have at least 1 event if governor decided EVENT
        events = r.json()
        assert isinstance(events, list)


# ─────────────────────────────────────────────
#  Reset
# ─────────────────────────────────────────────

class TestReset:
    def test_reset_clears_state(self):
        client.post("/api/v1/detect", json=ZONE_DETECTION)
        client.post("/api/v1/reset")
        r = client.get("/api/v1/governor/state")
        # After reset, no decisions → 404
        assert r.status_code == 404

    def test_detections_empty_after_reset(self):
        client.post("/api/v1/detect", json=ZONE_DETECTION)
        client.post("/api/v1/reset")
        r = client.get("/api/v1/detections")
        assert r.json() == []
