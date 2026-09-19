"""
PROJECT S.I.G.H.T. — Flight Control & WebSocket API Test Suite
Verifies genuine simulator integration endpoints in FastAPI backend.
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import app, _init_adapter


@pytest.fixture(autouse=True)
def ensure_fallback_adapter():
    """Ensure tests run against the predictable FallbackAdapter."""
    _init_adapter(mode="fallback")


def test_flight_status_endpoint():
    client = TestClient(app)
    response = client.get("/api/v1/flight/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "mode" in data
    assert "is_connected" in data
    assert "is_armed" in data
    assert "flight_mode" in data
    assert "link_status" in data
    assert "battery_percent" in data
    assert "altitude_m" in data


def test_flight_connect_and_disconnect():
    client = TestClient(app)
    # Connect in fallback mode
    res = client.post("/api/v1/flight/connect", json={"mode": "fallback", "port": 14550})
    assert res.status_code == 200
    assert res.json()["status"] in ["OK", "CONNECTING"]
    assert res.json()["mode"] == "fallback"

    # Disconnect
    res_disc = client.post("/api/v1/flight/disconnect")
    assert res_disc.status_code == 200
    assert res_disc.json()["status"] == "DISCONNECTED"


def test_flight_command_lifecycle():
    client = TestClient(app)
    # 1. Connect
    client.post("/api/v1/flight/connect", json={"mode": "fallback"})

    # 2. Arm
    arm_res = client.post("/api/v1/flight/arm")
    assert arm_res.status_code == 200
    assert arm_res.json()["status"] == "ARMED"

    # 3. Takeoff
    takeoff_res = client.post("/api/v1/flight/takeoff", json={"altitude": 20.0})
    assert takeoff_res.status_code == 200
    assert takeoff_res.json()["status"] == "TAKEOFF_COMMANDED"
    assert takeoff_res.json()["altitude_m"] == 20.0

    # 4. Move
    move_res = client.post("/api/v1/flight/move", json={"vx": 5.0, "vy": 0.0, "vz": 0.0, "yaw_rate": 0.0})
    assert move_res.status_code == 200
    assert move_res.json()["status"] == "MOVE_COMMANDED"

    # 5. Heading
    hdg_res = client.post("/api/v1/flight/heading", json={"heading": 180.0})
    assert hdg_res.status_code == 200
    assert hdg_res.json()["status"] == "HEADING_COMMANDED"
    assert hdg_res.json()["heading"] == 180.0

    # 6. Hover
    hover_res = client.post("/api/v1/flight/hover")
    assert hover_res.status_code == 200
    assert hover_res.json()["status"] == "HOVER_COMMANDED"

    # 7. Land
    land_res = client.post("/api/v1/flight/land")
    assert land_res.status_code == 200
    assert land_res.json()["status"] == "LAND_COMMANDED"

    # 8. RTH
    rth_res = client.post("/api/v1/flight/rth")
    assert rth_res.status_code == 200
    assert rth_res.json()["status"] == "RTH_COMMANDED"

    # 9. Disarm
    disarm_res = client.post("/api/v1/flight/disarm")
    assert disarm_res.status_code == 200


def test_websocket_telemetry_stream():
    client = TestClient(app)
    with client.websocket_connect("/ws") as websocket:
        init_data = websocket.receive_json()
        assert init_data["type"] == "init"
        assert "telemetry" in init_data
        assert "mode" in init_data

        # Ping-pong test
        websocket.send_json({"action": "ping"})
        pong_data = websocket.receive_json()
        assert pong_data["type"] == "pong"
