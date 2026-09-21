"""
PROJECT S.I.G.H.T. — Simulator Adapters Test Suite
Verifies adapter contracts, state management, and flight command execution.
"""

import pytest
import asyncio
from simulator.adapters.base_adapter import BaseSimulatorAdapter
from simulator.adapters.px4_adapter import PX4Adapter
from simulator.adapters.cloud_adapter import CloudAdapter
from simulator.adapters.fallback_adapter import FallbackAdapter
from simulator.telemetry.telemetry_models import SimulatorTelemetry


def test_fallback_adapter_lifecycle():
    async def _test():
        adapter = FallbackAdapter(mavlink_port=14555)
        assert adapter.mode_name == "fallback"
        assert not adapter.is_connected
        assert not adapter.is_armed

        # Connect
        assert await adapter.connect() is True
        assert adapter.is_connected is True

        # Arm
        assert await adapter.arm() is True
        assert adapter.is_armed is True

        # Takeoff
        assert await adapter.takeoff(altitude=25.0) is True

        # Heading
        assert await adapter.set_heading(270.0) is True

        # Move
        assert await adapter.move(vx=3.0, vy=1.0, vz=0.0) is True

        # Telemetry
        telem = await adapter.get_telemetry()
        assert "lat" in telem
        assert "lng" in telem
        assert "altitude" in telem
        assert "headingDegrees" in telem
        assert telem["isArmed"] is True

        # Land
        assert await adapter.land() is True

        # Disarm
        await adapter.disarm()

        # Disconnect
        await adapter.disconnect()
        assert not adapter.is_connected

    asyncio.run(_test())



def test_cloud_adapter_configuration():
    cloud = CloudAdapter(host="192.168.1.100", port=14550)
    assert cloud.mode_name == "cloud"
    assert cloud.host == "192.168.1.100"
    assert cloud.port == 14550
    assert "192.168.1.100:14550" in cloud.connection_string


def test_udp_endpoint_mode_selection_matches_live_mavproxy_topology():
    assert PX4Adapter._udp_input_mode("udp:172.30.16.1:14550") is True
    assert PX4Adapter._udp_input_mode("udpin:0.0.0.0:14550") is True
    assert PX4Adapter._udp_input_mode("udpout:172.30.16.1:14550") is False


@pytest.mark.asyncio
async def test_px4_adapter_move_sends_body_ned_velocity_pulse_and_stops():
    from types import SimpleNamespace
    from simulator.adapters.px4_adapter import PX4Adapter

    adapter = PX4Adapter(connection_string="udp:172.30.16.1:14550")
    sent_packets = []

    class FakeMav:
        def set_position_target_local_ned_send(self, *args):
            sent_packets.append(args)

    adapter._master = SimpleNamespace(mav=FakeMav())
    adapter._move_duration_s = 0.25
    adapter._move_interval_s = 0.05

    ok = await adapter.move(vx=1.5, vy=2.0, vz=-0.5, yaw_rate=30.0)

    assert ok is True
    assert len(sent_packets) >= 2
    first = sent_packets[0]
    assert first[3] == 8  # MAV_FRAME_BODY_NED
    assert first[8] == pytest.approx(1.5)
    assert first[9] == pytest.approx(2.0)
    assert first[10] == pytest.approx(-0.5)
    assert sent_packets[-1][8] == pytest.approx(0.0)
    assert sent_packets[-1][9] == pytest.approx(0.0)
    assert sent_packets[-1][10] == pytest.approx(0.0)


@pytest.mark.asyncio
async def test_px4_adapter_move_rejects_non_finite_and_absurd_values():
    from types import SimpleNamespace
    from simulator.adapters.px4_adapter import PX4Adapter

    adapter = PX4Adapter(connection_string="udp:172.30.16.1:14550")

    class FakeMav:
        def set_position_target_local_ned_send(self, *args):
            return None

    adapter._master = SimpleNamespace(mav=FakeMav())

    assert await adapter.move(float("nan"), 0.0, 0.0, 0.0) is False
    assert await adapter.move(float("inf"), 0.0, 0.0, 0.0) is False
    assert await adapter.move(99.0, 0.0, 0.0, 0.0) is False
    assert await adapter.move(0.0, 0.0, 0.0, 0.0) is True


def test_telemetry_model_schema_conversion():
    telem = SimulatorTelemetry(
        latitude=34.0522,
        longitude=-117.8247,
        altitude_m=84.5,
        ground_speed_mps=12.4,
        heading_deg=90.0,
        battery_percent=88.2,
        is_armed=True,
        flight_mode="AUTO_MISSION"
    )

    cc_schema = telem.to_command_centre_schema()
    assert cc_schema["lat"] == 34.0522
    assert cc_schema["lng"] == -117.8247
    assert cc_schema["altitude"] == 84.5
    assert cc_schema["speed"] == 12.4
    assert cc_schema["heading"] == "E"
    assert cc_schema["headingDegrees"] == 90.0
    assert cc_schema["battery"] == 88.2
    assert cc_schema["isArmed"] is True
    assert cc_schema["flightMode"] == "AUTO_MISSION"
    assert cc_schema["linkStatus"] == "ONLINE"

    gov_context = telem.to_governor_context()
    assert gov_context["uav_id"] == "SIGHT-UAV-01"
    assert gov_context["battery_percent"] == 88.2
    assert gov_context["is_armed"] is True
