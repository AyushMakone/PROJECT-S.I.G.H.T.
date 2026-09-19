"""
PROJECT S.I.G.H.T. - Flight Lifecycle Test Suite
Verifies Arm, Takeoff, Waypoint Navigation, Landing, and Disarm sequence.
"""

import pytest
import os
from pathlib import Path
from simulator.simulator_interface import SimulatorInterface
from simulator.px4.autopilot_state import FlightMode

@pytest.fixture
def simulator():
    sim = SimulatorInterface(mavlink_port=14552) # Test port
    sim.reset()
    yield sim
    sim.stop()

def test_arm_and_disarm(simulator):
    # Initial state
    telem = simulator.get_telemetry()
    assert not telem["is_armed"]
    assert telem["flight_mode"] == "DISARMED"

    # Arm
    assert simulator.arm() is True
    telem = simulator.get_telemetry()
    assert telem["is_armed"] is True
    assert telem["flight_mode"] == "ARMED"

    # Disarm while on ground
    assert simulator.disarm() is True
    telem = simulator.get_telemetry()
    assert telem["is_armed"] is False
    assert telem["flight_mode"] == "DISARMED"

def test_takeoff_sequence(simulator):
    simulator.arm()
    assert simulator.takeoff(altitude_m=50.0) is True

    # Step physics until takeoff reaches target
    for _ in range(25):
        telem = simulator.step(dt=1.0)
        if telem["altitude_m"] >= 50.0:
            break

    telem = simulator.get_telemetry()
    assert telem["altitude_m"] >= 49.0
    assert telem["is_armed"] is True
    assert telem["flight_mode"] in ["LOITER", "AUTO_MISSION", "TAKEOFF"]

def test_waypoint_mission_and_landing(simulator):
    candidate_path1 = Path(__file__).resolve().parent.parent / "missions" / "perimeter_mission.json"
    candidate_path2 = Path(__file__).resolve().parent.parent.parent / "simulator" / "missions" / "perimeter_mission.json"
    mission_path = str(candidate_path1 if candidate_path1.exists() else candidate_path2)
    assert os.path.exists(mission_path)

    # Load mission
    assert simulator.load_mission(mission_path) is True
    telem = simulator.get_telemetry()
    assert telem["total_waypoints"] == 5

    # Arm and Takeoff
    simulator.arm()
    simulator.takeoff(altitude_m=84.0)

    # Step takeoff
    for _ in range(30):
        simulator.step(dt=1.0)

    # Run mission
    assert simulator.run_mission() is True
    telem = simulator.get_telemetry()
    assert telem["flight_mode"] == "AUTO_MISSION"

    # Step through mission waypoints
    for _ in range(60):
        telem = simulator.step(dt=1.5)
        # Verify battery discharges under motor load
        assert telem["battery_percent"] < 100.0

    # Command landing
    simulator.land()
    telem = simulator.get_telemetry()
    assert telem["flight_mode"] == "LANDING"

    # Step landing to touchdown
    for _ in range(50):
        telem = simulator.step(dt=1.0)
        if telem["flight_mode"] == "LANDED":
            break

    assert telem["altitude_m"] <= 0.5
    assert telem["flight_mode"] in ["LANDED", "DISARMED"]
    assert telem["is_armed"] is False
