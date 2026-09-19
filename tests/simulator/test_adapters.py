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
