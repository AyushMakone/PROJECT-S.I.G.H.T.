import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from fastapi.testclient import TestClient
from backend.main import app
from simulator.telemetry.telemetry_models import SimulatorTelemetry

client = TestClient(app)


def test_health_canonical_contract():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "sight-simulator-backend"


def test_runtime_status_contract():
    response = client.get("/api/v1/runtime/status")
    assert response.status_code == 200
    data = response.json()
    assert data["runtime"] == "ardupilot_sitl"
    assert "connected" in data
    assert "system_id" in data
    assert "component_id" in data


def test_runtime_connect_and_disconnect():
    connect = client.post("/api/v1/runtime/connect", json={"connection": "udp:127.0.0.1:14550"})
    assert connect.status_code == 200
    payload = connect.json()
    assert payload["connection"] == "udp:127.0.0.1:14550"
    assert isinstance(payload["connected"], bool)

    disconnect = client.post("/api/v1/runtime/disconnect")
    assert disconnect.status_code == 200


def test_missing_telemetry_fields_are_honest_and_non_crashing():
    telem = SimulatorTelemetry()
    payload = telem.to_command_centre_schema()

    assert payload["altitude"] is None
    assert payload["speed"] is None
    assert payload["heading"] in (None, "UNKNOWN")
    assert payload["headingDegrees"] is None
    assert payload["battery"] is None
    assert payload["gpsStatus"] in ("UNKNOWN", "NO_FIX")


def test_runtime_status_uses_live_adapter_state_not_stale_snapshot():
    import backend.main as backend_main

    class DummyAdapter:
        is_connected = False

    backend_main._sim_adapter = DummyAdapter()
    backend_main._runtime_state["connected"] = True
    backend_main._runtime_state["system_id"] = 99
    backend_main._runtime_state["component_id"] = 99

    response = client.get("/api/v1/runtime/status")
    assert response.status_code == 200
    assert response.json()["connected"] is False
