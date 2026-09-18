"""
PROJECT S.I.G.H.T. - MAVLink 2.0 UDP Server for PX4 SITL Telemetry
Broadcasts standard MAVLink messages (HEARTBEAT, GLOBAL_POSITION_INT, ATTITUDE, SYS_STATUS)
and handles incoming command packets over UDP network sockets.
"""

import time
import socket
import threading
from typing import Optional
from pymavlink import mavutil
from .autopilot_state import AutopilotStateMachine, FlightMode

class MAVLinkServer:
    """
    True MAVLink 2.0 network server interfacing AutopilotStateMachine.
    Listens and broadcasts over UDP port (default 14550 for GCS / 14540 for companion computer).
    """
    def __init__(self, autopilot: AutopilotStateMachine, host: str = "127.0.0.1", port: int = 14550):
        self.autopilot = autopilot
        self.host = host
        self.port = port
        self.running = False
        self.thread: Optional[threading.Thread] = None

        # System identity
        self.system_id = 1
        self.component_id = 1 # MAV_COMP_ID_AUTOPILOT1
        self.boot_time_ms = int(time.time() * 1000)

        # MAVLink connection
        self.mav_out = None
        self.listen_sock = None

    def start(self):
        if self.running:
            return
        self.running = True

        # Initialize pymavlink UDP output connection
        # Sends packets to host:port
        self.mav_out = mavutil.mavlink_connection(
            f"udpout:{self.host}:{self.port}",
            source_system=self.system_id,
            source_component=self.component_id
        )

        self.thread = threading.Thread(target=self._broadcast_loop, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        if self.mav_out:
            self.mav_out.close()
            self.mav_out = None

    def _broadcast_loop(self):
        """
        Broadcasting MAVLink telemetry loop at 10 Hz.
        """
        last_heartbeat = 0.0

        while self.running:
            now = time.time()
            now_ms = int(now * 1000) - self.boot_time_ms
            telem = self.autopilot.get_telemetry()

            # 1. Send HEARTBEAT at 1 Hz
            if now - last_heartbeat >= 1.0:
                base_mode = mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED
                if telem.is_armed:
                    base_mode |= mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED
                
                # PX4 custom mode mapping
                custom_mode = 0
                if telem.flight_mode == FlightMode.AUTO_MISSION:
                    custom_mode = 4 # Auto Mission
                elif telem.flight_mode == FlightMode.TAKEOFF:
                    custom_mode = 2 # Takeoff
                elif telem.flight_mode == FlightMode.LANDING:
                    custom_mode = 6 # Land

                self.mav_out.mav.heartbeat_send(
                    mavutil.mavlink.MAV_TYPE_QUADROTOR,
                    mavutil.mavlink.MAV_AUTOPILOT_PX4,
                    base_mode,
                    custom_mode,
                    mavutil.mavlink.MAV_STATE_ACTIVE if telem.is_armed else mavutil.mavlink.MAV_STATE_STANDBY
                )
                last_heartbeat = now

            # 2. Send GLOBAL_POSITION_INT at 10 Hz
            lat_int = int(telem.lat * 1e7)
            lon_int = int(telem.lng * 1e7)
            alt_mm = int(telem.altitude_m * 1000)
            hdg_cdeg = int((telem.heading_deg % 360) * 100)

            # Speed vector components
            import math
            vx_cm = int(telem.speed_mps * math.cos(math.radians(telem.heading_deg)) * 100)
            vy_cm = int(telem.speed_mps * math.sin(math.radians(telem.heading_deg)) * 100)
            vz_cm = int(-telem.climb_rate_mps * 100)

            self.mav_out.mav.global_position_int_send(
                now_ms,
                lat_int,
                lon_int,
                alt_mm,
                alt_mm, # relative alt
                vx_cm,
                vy_cm,
                vz_cm,
                hdg_cdeg
            )

            # 3. Send ATTITUDE at 10 Hz
            self.mav_out.mav.attitude_send(
                now_ms,
                math.radians(telem.roll_deg),
                math.radians(telem.pitch_deg),
                math.radians(telem.yaw_deg),
                0.0, 0.0, 0.0 # angular speeds
            )

            # 4. Send SYS_STATUS at 2 Hz
            self.mav_out.mav.sys_status_send(
                0xFFFFFFFF, # sensors present
                0xFFFFFFFF, # sensors enabled
                0xFFFFFFFF, # sensors health
                500,        # 50% CPU load
                int(telem.battery_voltage_v * 1000), # mV
                -1,         # current battery
                int(telem.battery_percent), # battery remaining %
                0, 0, 0, 0, 0, 0
            )

            time.sleep(0.1)
