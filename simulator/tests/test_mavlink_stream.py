"""
PROJECT S.I.G.H.T. - MAVLink Telemetry Stream Test
Verifies that the simulator broadcasts standard MAVLink 2.0 packets over UDP
and that an external receiver can decode HEARTBEAT and GLOBAL_POSITION_INT.
"""

import time
import pytest
from pymavlink import mavutil
from simulator.simulator_interface import SimulatorInterface

def test_mavlink_udp_telemetry_broadcast():
    test_port = 14558 # dedicated test port
    sim = SimulatorInterface(mavlink_port=test_port)
    sim.reset()
    sim.start(enable_mavlink=True)

    receiver = None
    try:
        # Connect MAVLink UDP listener to the broadcast port
        receiver = mavutil.mavlink_connection(f"udpin:127.0.0.1:{test_port}")

        # Wait for HEARTBEAT
        heartbeat_msg = receiver.recv_match(type="HEARTBEAT", blocking=True, timeout=3.0)
        assert heartbeat_msg is not None, "Failed to receive MAVLink HEARTBEAT message"
        assert heartbeat_msg.type == mavutil.mavlink.MAV_TYPE_QUADROTOR
        assert heartbeat_msg.autopilot == mavutil.mavlink.MAV_AUTOPILOT_PX4

        # Wait for GLOBAL_POSITION_INT
        pos_msg = receiver.recv_match(type="GLOBAL_POSITION_INT", blocking=True, timeout=3.0)
        assert pos_msg is not None, "Failed to receive MAVLink GLOBAL_POSITION_INT message"
        
        # Verify coordinates are non-zero and match proving ground scale (approx 34.05N, -117.82W)
        received_lat = pos_msg.lat / 1e7
        received_lon = pos_msg.lon / 1e7
        assert 33.0 < received_lat < 35.0
        assert -119.0 < received_lon < -116.0

        # Wait for SYS_STATUS (Battery)
        status_msg = receiver.recv_match(type="SYS_STATUS", blocking=True, timeout=3.0)
        assert status_msg is not None, "Failed to receive MAVLink SYS_STATUS message"
        assert 0 <= status_msg.battery_remaining <= 100

    finally:
        if receiver:
            receiver.close()
        sim.stop()
