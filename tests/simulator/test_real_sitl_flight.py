"""
PROJECT S.I.G.H.T. — Real SITL Flight Integration Test
=======================================================

Automated integration test that executes the full standalone probe sequence
against a genuine ArduPilot SITL instance:

    CONNECT → TELEMETRY → ARM → TAKEOFF → VERIFY ASCENT → MOVE → LAND → VERIFY

This test requires a live ArduPilot SITL process:

    # Linux / WSL:
    ArduCopter --home=28.7041,77.1025,200,0 --model=quad --speedup=5 \
               --defaults ArduCopter.param --sim-port-in=5502

    # Windows (Cygwin):
    ArduCopter-4.5.7.elf --home=28.7041,77.1025,200,0 --model=quad

When SITL is not running, the test is automatically skipped via the
`requires_sitl` marker. It will never fail CI if the simulator is absent.

Usage:
    # Run integration tests (requires running SITL):
    pytest tests/simulator/test_real_sitl_flight.py -v -m "sitl"

    # Run unit tests only (CI-safe, skips SITL):
    pytest tests/ -m "not sitl"
"""

import asyncio
import os
import socket
import time
import pytest
import sys

# ─────────────────────────────────────────────────────────────────────────────
#  Project path bootstrap
# ─────────────────────────────────────────────────────────────────────────────
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# ─────────────────────────────────────────────────────────────────────────────
#  Probe constants (match standalone_probe.py verified trace)
# ─────────────────────────────────────────────────────────────────────────────
SITL_ENDPOINT = os.getenv("MAVLINK_ENDPOINT", "tcp:127.0.0.1:5760")
TAKEOFF_ALTITUDE_M = float(os.getenv("SITL_TAKEOFF_ALT", "10.0"))
TAKEOFF_TIMEOUT_S = 30.0
MOVE_DURATION_S = 5.0
MOVE_SPEED_MPS = 2.5


def _sitl_reachable(endpoint: str = SITL_ENDPOINT, timeout: float = 1.0) -> bool:
    """
    Probe TCP/IP reachability of the SITL endpoint without importing pymavlink.
    Returns True only if a TCP connection succeeds within `timeout` seconds.
    Supports tcp: and udpin: endpoint formats.
    """
    try:
        if endpoint.startswith("tcp:"):
            parts = endpoint.replace("tcp:", "").split(":")
            host, port = parts[0], int(parts[1])
        elif "udpin:" in endpoint or "udpout:" in endpoint:
            # UDP is connectionless — we attempt TCP probe on same host/port
            parts = endpoint.split(":")
            host = parts[-2].replace("0.0.0.0", "127.0.0.1")
            port = int(parts[-1])
        else:
            return False

        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, ValueError):
        return False


# Mark: requires a live ArduPilot SITL
requires_sitl = pytest.mark.skipif(
    not _sitl_reachable(),
    reason=(
        f"ArduPilot SITL not reachable on {SITL_ENDPOINT}. "
        "Start SITL first: 'ArduCopter --home=28.7041,77.1025,200,0 --model=quad'"
    )
)


# ─────────────────────────────────────────────────────────────────────────────
#  Unit-level Tests (CI-safe, no SITL required)
# ─────────────────────────────────────────────────────────────────────────────

class TestPX4AdapterUnit:
    """
    Unit tests for the PX4Adapter that run without an active SITL process.
    Verify instantiation, default endpoint, and internal state.
    """

    def test_adapter_instantiation_default_endpoint(self):
        """PX4Adapter should instantiate with ArduPilot TCP default endpoint."""
        from simulator.adapters.px4_adapter import PX4Adapter
        adapter = PX4Adapter()
        assert "tcp" in adapter.connection_string or "udp" in adapter.connection_string
        assert not adapter.is_connected
        assert not adapter.is_armed
        assert adapter.flight_mode == "DISARMED"

    def test_adapter_custom_endpoint(self):
        """PX4Adapter should store a custom TCP endpoint correctly."""
        from simulator.adapters.px4_adapter import PX4Adapter
        adapter = PX4Adapter(connection_string="tcp:127.0.0.1:5760")
        assert adapter.connection_string == "tcp:127.0.0.1:5760"

    def test_adapter_udp_endpoint(self):
        """PX4Adapter should support UDP endpoint for PX4 SITL."""
        from simulator.adapters.px4_adapter import PX4Adapter
        adapter = PX4Adapter(connection_string="udpin:0.0.0.0:14550")
        assert "14550" in adapter.connection_string

    def test_ardupilot_mode_table(self):
        """ArduPilot mode table must contain required flight modes."""
        from simulator.adapters.px4_adapter import _ARDUPILOT_MODES
        assert _ARDUPILOT_MODES[4] == "GUIDED"
        assert _ARDUPILOT_MODES[5] == "LOITER"
        assert _ARDUPILOT_MODES[6] == "RTL"
        assert _ARDUPILOT_MODES[9] == "LAND"

    def test_px4_mode_table(self):
        """PX4 mode table must contain required main modes."""
        from simulator.adapters.px4_adapter import _PX4_MAIN_MODES
        assert _PX4_MAIN_MODES[5] == "AUTO_LOITER"
        assert _PX4_MAIN_MODES[6] == "AUTO_RTL"

    def test_telemetry_initial_state(self):
        """Adapter telemetry store should start in a clean state."""
        from simulator.adapters.px4_adapter import PX4Adapter
        adapter = PX4Adapter()
        telem = adapter.telemetry
        assert telem.is_armed is False
        assert telem.flight_mode == "DISARMED"
        assert telem.link_status in ("OFFLINE", "ONLINE", "LOST", None, "")

    @pytest.mark.asyncio
    async def test_commands_gracefully_fail_when_disconnected(self):
        """Flight commands must return False (not raise) when no MAVLink connection exists."""
        from simulator.adapters.px4_adapter import PX4Adapter
        adapter = PX4Adapter(connection_string="tcp:127.0.0.1:59999")  # unused port
        assert await adapter.arm() is False
        assert await adapter.disarm() is False
        assert await adapter.land() is False
        assert await adapter.move(1.0, 0.0, 0.0) is False
        assert await adapter.set_heading(90.0) is False

    @pytest.mark.asyncio
    async def test_get_telemetry_returns_dict(self):
        """get_telemetry() must return a dictionary with expected keys even when disconnected."""
        from simulator.adapters.px4_adapter import PX4Adapter
        adapter = PX4Adapter()
        telem = await adapter.get_telemetry()
        assert isinstance(telem, dict)
        for key in ("lat", "lng", "altitude", "speed", "headingDegrees", "battery", "isArmed", "flightMode"):
            assert key in telem, f"Key '{key}' missing from telemetry dict"


# ─────────────────────────────────────────────────────────────────────────────
#  Integration Tests (require live ArduPilot SITL)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.sitl
@requires_sitl
class TestRealSITLFlight:
    """
    Full live flight integration test against genuine ArduPilot SITL.
    Reproduces the standalone probe sequence from docs/REAL_SIMULATOR_IMPLEMENTATION_PLAN.md
    Section 4 (Standalone Probe Verification Results).

    All 6 probe stages must pass sequentially:
      [PROBE 1/6] CONNECT
      [PROBE 2/6] READ TELEMETRY
      [PROBE 3/6] ARMING VERIFICATION
      [PROBE 4/6] TAKEOFF VERIFICATION
      [PROBE 5/6] MOVE DYNAMICS VERIFICATION
      [PROBE 6/6] LANDING VERIFICATION
    """

    @pytest.fixture(scope="class")
    def event_loop(self):
        """Provide a shared event loop for the class-scoped tests."""
        loop = asyncio.new_event_loop()
        yield loop
        loop.close()

    @pytest.fixture(scope="class")
    async def sitl_adapter(self):
        """
        Create, connect, and tear down a PX4Adapter pointed at the live SITL endpoint.
        Scoped to class so the same MAVLink connection is reused across test methods.
        """
        from simulator.adapters.px4_adapter import PX4Adapter
        adapter = PX4Adapter(connection_string=SITL_ENDPOINT)
        connected = await adapter.connect()
        assert connected, f"[PROBE 1/6] CONNECT FAILED: could not reach SITL on {SITL_ENDPOINT}"
        yield adapter
        await adapter.disconnect()

    @pytest.mark.asyncio
    async def test_probe_1_connect(self, sitl_adapter):
        """[PROBE 1/6] CONNECT — adapter must be connected after connect()."""
        assert sitl_adapter.is_connected, (
            f"[PROBE 1/6] FAILED: not connected after await connect() on {SITL_ENDPOINT}"
        )

    @pytest.mark.asyncio
    async def test_probe_2_telemetry(self, sitl_adapter):
        """[PROBE 2/6] READ TELEMETRY — simulator must emit valid telemetry fields."""
        # Allow up to 5 seconds for heartbeat and telemetry
        await asyncio.sleep(3.0)
        telem = await sitl_adapter.get_telemetry()

        assert isinstance(telem, dict), "[PROBE 2/6] FAILED: telemetry is not a dict"

        # GPS position must be plausible (lat/lng not both 0)
        lat = telem.get("lat", 0.0)
        lng = telem.get("lng", 0.0)
        assert not (lat == 0.0 and lng == 0.0), (
            "[PROBE 2/6] FAILED: lat=0, lng=0 — SITL GPS not emitting"
        )

        # Battery must be a valid percentage
        battery = telem.get("battery", -1)
        assert 0 <= battery <= 100, f"[PROBE 2/6] FAILED: battery={battery}% out of valid range"

        print(f"\n[PROBE 2/6] PASSED: lat={lat:.5f} lng={lng:.5f} battery={battery}%")

    @pytest.mark.asyncio
    async def test_probe_3_arm(self, sitl_adapter):
        """[PROBE 3/6] ARMING — adapter must report is_armed=True after ARM command."""
        # Initialize SITL params (ARMING_CHECK=0)
        if hasattr(sitl_adapter, "init_sitl_params"):
            await sitl_adapter.init_sitl_params()
            await asyncio.sleep(0.5)

        armed = await sitl_adapter.arm()
        assert armed, "[PROBE 3/6] ARM command returned False"

        # Wait up to 5s for armed state to propagate via HEARTBEAT
        deadline = time.time() + 5.0
        while time.time() < deadline:
            if sitl_adapter.is_armed:
                break
            await asyncio.sleep(0.2)

        assert sitl_adapter.is_armed, (
            "[PROBE 3/6] FAILED: motors not armed after 5s wait "
            "(HEARTBEAT armed flag not set)"
        )
        print("\n[PROBE 3/6] PASSED: Motors armed in SITL")

    @pytest.mark.asyncio
    async def test_probe_4_takeoff(self, sitl_adapter):
        """[PROBE 4/6] TAKEOFF — altitude must reach ≥80% of commanded altitude."""
        alt_before = (await sitl_adapter.get_telemetry()).get("altitude", 0.0)
        success = await sitl_adapter.takeoff(altitude=TAKEOFF_ALTITUDE_M)
        assert success, "[PROBE 4/6] TAKEOFF command returned False"

        # Poll altitude for TAKEOFF_TIMEOUT_S
        achieved_alt = alt_before
        deadline = time.time() + TAKEOFF_TIMEOUT_S
        while time.time() < deadline:
            telem = await sitl_adapter.get_telemetry()
            achieved_alt = telem.get("altitude", alt_before)
            if achieved_alt >= TAKEOFF_ALTITUDE_M * 0.80:
                break
            await asyncio.sleep(1.0)

        target_80pct = TAKEOFF_ALTITUDE_M * 0.80
        assert achieved_alt >= target_80pct, (
            f"[PROBE 4/6] FAILED: altitude {achieved_alt:.2f}m < "
            f"80% of {TAKEOFF_ALTITUDE_M}m target ({target_80pct:.2f}m) "
            f"after {TAKEOFF_TIMEOUT_S}s"
        )
        print(f"\n[PROBE 4/6] PASSED: altitude reached {achieved_alt:.2f}m "
              f"(target {TAKEOFF_ALTITUDE_M}m)")

    @pytest.mark.asyncio
    async def test_probe_5_move(self, sitl_adapter):
        """[PROBE 5/6] MOVE — groundspeed must increase after forward velocity command."""
        telem_before = await sitl_adapter.get_telemetry()
        lat_before = telem_before.get("lat", 0.0)

        move_ok = await sitl_adapter.move(vx=MOVE_SPEED_MPS, vy=0.0, vz=0.0)
        assert move_ok, "[PROBE 5/6] MOVE command returned False"

        await asyncio.sleep(MOVE_DURATION_S)

        telem_after = await sitl_adapter.get_telemetry()
        speed_after = telem_after.get("speed", 0.0)
        lat_after = telem_after.get("lat", lat_before)

        assert speed_after > 0.5 or abs(lat_after - lat_before) > 0.00001, (
            f"[PROBE 5/6] FAILED: no movement detected. speed={speed_after:.2f} m/s, "
            f"lat_delta={abs(lat_after - lat_before):.6f}°"
        )
        print(f"\n[PROBE 5/6] PASSED: groundspeed={speed_after:.2f} m/s, "
              f"lat_delta={abs(lat_after - lat_before):.6f}°")

    @pytest.mark.asyncio
    async def test_probe_6_land(self, sitl_adapter):
        """[PROBE 6/6] LAND — altitude must decrease to near zero after LAND command."""
        telem_before = await sitl_adapter.get_telemetry()
        alt_before = telem_before.get("altitude", 0.0)

        land_ok = await sitl_adapter.land()
        assert land_ok, "[PROBE 6/6] LAND command returned False"

        # Allow up to 60s for landing
        deadline = time.time() + 60.0
        final_alt = alt_before
        while time.time() < deadline:
            telem = await sitl_adapter.get_telemetry()
            final_alt = telem.get("altitude", alt_before)
            if final_alt < 1.0:
                break
            await asyncio.sleep(2.0)

        # Accept landed if altitude is below 2m (absolute) or 95% reduction
        alt_drop = alt_before - final_alt
        assert final_alt < 2.0 or alt_drop > alt_before * 0.90, (
            f"[PROBE 6/6] FAILED: altitude {final_alt:.2f}m too high after LAND "
            f"(started at {alt_before:.2f}m)"
        )
        print(f"\n[PROBE 6/6] PASSED: landed at {final_alt:.2f}m "
              f"(started {alt_before:.2f}m)")
