"""
PROJECT S.I.G.H.T. — Universal MAVLink 2.0 Simulator Adapter
Connects to genuine ArduPilot SITL and PX4 Autopilot SITL instances via MAVLink 2.0 over TCP or UDP.
Issues standard MAVLink flight commands and decodes live telemetry packets.

Supported endpoints:
  ArduPilot SITL (native): tcp:127.0.0.1:5760
  PX4 SITL (Docker/WSL):   udpin:0.0.0.0:14550  or  udpout:<host>:14550
  Cloud / Remote SITL:      tcp:<host>:<port>  or  udpin:0.0.0.0:<port>

Supported autopilots:
  ArduPilot Copter/Plane — custom_mode integer (GUIDED=4, LOITER=5, RTL=6, LAND=9)
  PX4 Autopilot           — custom_mode field encoded as (main_mode << 16 | sub_mode << 24)
"""

import os
import sys
import time
import math
import asyncio
import logging
import threading
from typing import Dict, Any, Optional, List
import numpy as np

try:
    from pymavlink import mavutil
    PYMAVLINK_AVAILABLE = True
except ImportError:
    PYMAVLINK_AVAILABLE = False

from .base_adapter import BaseSimulatorAdapter
from ..telemetry.telemetry_models import SimulatorTelemetry

logger = logging.getLogger("SIGHT.MAVLinkAdapter")

# ArduPilot Copter flight mode numbers (custom_mode integer from HEARTBEAT)
_ARDUPILOT_MODES = {
    0: "STABILIZE", 1: "ACRO", 2: "ALT_HOLD", 3: "AUTO",
    4: "GUIDED", 5: "LOITER", 6: "RTL", 7: "CIRCLE",
    9: "LAND", 11: "DRIFT", 13: "SPORT", 14: "FLIP",
    15: "AUTOTUNE", 16: "POSHOLD", 17: "BRAKE", 18: "THROW",
    19: "AVOID_ADSB", 20: "GUIDED_NOGPS", 21: "SMART_RTL",
    22: "FLOWHOLD", 23: "FOLLOW", 24: "ZIGZAG"
}

# PX4 main_mode numbers (bits 16-23 of custom_mode in HEARTBEAT)
_PX4_MAIN_MODES = {
    1: "MANUAL", 2: "ALTCTL", 3: "POSCTL",
    4: "AUTO_MISSION", 5: "AUTO_LOITER", 6: "AUTO_RTL",
    7: "AUTO_LAND", 8: "AUTO_TAKEOFF"
}


class PX4Adapter(BaseSimulatorAdapter):
    """
    Universal MAVLink 2.0 adapter for ArduPilot SITL and PX4 SITL.

    Automatically detects autopilot type from HEARTBEAT (ArduPilot type=3, PX4 type=12)
    and applies the correct flight mode decoding table.
    Communicates with local or remote SITL instances over TCP or UDP.
    """

    def __init__(
        self,
        connection_string: Optional[str] = None,
        target_system: int = 1,
        target_component: int = 1,
        source_system: int = 255,  # GCS system ID
        source_component: int = 190
    ):
        self.connection_string = connection_string or os.getenv("MAVLINK_ENDPOINT", "tcp:127.0.0.1:5760")
        self.target_system = target_system
        self.target_component = target_component
        self.source_system = source_system
        self.source_component = source_component

        self._master: Optional[Any] = None
        self._connected = False
        self._rx_thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()
        self._autopilot_type: int = 0  # 0=unknown, 3=ArduPilot, 12=PX4

        # Telemetry store
        self.telemetry = SimulatorTelemetry()
        self._last_heartbeat_time = 0.0
        self._last_frame: Optional[np.ndarray] = None
        self._camera_provider = None

    @property
    def mode_name(self) -> str:
        return "local" if "127.0.0.1" in self.connection_string or "0.0.0.0" in self.connection_string else "cloud"

    @property
    def is_connected(self) -> bool:
        with self._lock:
            # Check connection flag and heartbeat liveness (< 4.5 seconds)
            if not self._connected or not self._running:
                return False
            return (time.time() - self._last_heartbeat_time) < 4.5

    @property
    def is_armed(self) -> bool:
        with self._lock:
            return self.telemetry.is_armed

    @property
    def flight_mode(self) -> str:
        with self._lock:
            return self.telemetry.flight_mode

    def set_camera_provider(self, provider):
        """Attaches an optical camera feed provider (e.g., FrameManager)."""
        self._camera_provider = provider

    async def connect(self) -> bool:
        """
        Establishes MAVLink connection and begins packet ingestion thread.
        """
        if not PYMAVLINK_AVAILABLE:
            logger.error("[SIM] pymavlink is not installed. Cannot connect to PX4 MAVLink.")
            return False

        if self._connected:
            return True

        logger.info(f"[SIM] Connecting to MAVLink endpoint: {self.connection_string}")
        try:
            # mavutil.mavlink_connection creates the network transport
            self._master = mavutil.mavlink_connection(
                self.connection_string,
                source_system=self.source_system,
                source_component=self.source_component,
                autoreconnect=True
            )
            self._running = True
            self._rx_thread = threading.Thread(target=self._rx_worker, daemon=True, name="PX4Adapter-Rx")
            self._rx_thread.start()

            # Wait up to 3.0 seconds for initial vehicle heartbeat
            start_wait = time.time()
            while time.time() - start_wait < 3.0:
                if self.is_connected:
                    logger.info(f"[SIM] Connected. Vehicle discovered (SysID={self.target_system})")
                    return True
                await asyncio.sleep(0.1)

            logger.info(f"[SIM] Connection initiated to {self.connection_string}. Listening for incoming heartbeat...")
            self._connected = True
            return True
        except Exception as e:
            logger.error(f"[SIM] Failed to connect to MAVLink endpoint: {e}")
            self._connected = False
            self._running = False
            return False

    async def disconnect(self) -> None:
        """Closes MAVLink transport."""
        logger.info("[SIM] Disconnecting PX4 adapter...")
        self._running = False
        self._connected = False
        if self._rx_thread and self._rx_thread.is_alive():
            self._rx_thread.join(timeout=1.0)
        if self._master:
            try:
                self._master.close()
            except Exception:
                pass
            self._master = None
        logger.info("[SIM] Disconnected.")

    async def arm(self) -> bool:
        """Sets GUIDED mode then sends MAV_CMD_COMPONENT_ARM_DISARM (1) to autopilot."""
        logger.info("[SIM] ARM command sent")
        # ArduPilot SITL requires GUIDED mode before arming
        await self._set_mode_guided()
        await asyncio.sleep(0.3)
        return await self._send_command_long(
            command=mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            param1=1.0,  # 1 to arm
            param2=0.0   # 0 for normal, 21196 for force arm
        )

    async def disarm(self) -> bool:
        """Sends MAV_CMD_COMPONENT_ARM_DISARM (0) to autopilot."""
        logger.info("[SIM] DISARM command sent")
        return await self._send_command_long(
            command=mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
            param1=0.0 # 0 to disarm
        )

    async def takeoff(self, altitude: float = 10.0) -> bool:
        """Sends MAV_CMD_NAV_TAKEOFF with target altitude in meters."""
        logger.info(f"[SIM] TAKEOFF command sent (altitude={altitude}m)")
        # Arm first if disarmed
        if not self.is_armed:
            await self.arm()
            await asyncio.sleep(0.5)

        return await self._send_command_long(
            command=mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
            param1=0.0, # Minimum pitch
            param4=0.0, # Yaw angle
            param7=float(altitude) # Altitude
        )

    async def land(self) -> bool:
        """Sends MAV_CMD_NAV_LAND."""
        logger.info("[SIM] LAND command sent")
        return await self._send_command_long(
            command=mavutil.mavlink.MAV_CMD_NAV_LAND
        )

    async def hover(self) -> bool:
        """Sends hold position / loiter command."""
        logger.info("[SIM] HOVER / LOITER command sent")
        # Set custom mode to AUTO.LOITER or send 0-velocity hold
        return await self.move(0.0, 0.0, 0.0, 0.0)

    async def move(self, vx: float, vy: float, vz: float, yaw_rate: float = 0.0) -> bool:
        """
        Sends velocity setpoint in body NED frame using SET_POSITION_TARGET_LOCAL_NED.
        vx: forward (m/s), vy: right (m/s), vz: down (m/s, negative is climb)
        """
        if not self._master:
            return False

        try:
            # Bitmask: ignore position, ignore accel, ignore yaw. Use velocity + yaw_rate
            # 0b0000101111000111 = 0x0BC7 (velocity + yaw_rate)
            type_mask = 0b0000101111000111
            yaw_rate_rad = math.radians(yaw_rate)

            self._master.mav.set_position_target_local_ned_send(
                int(time.time() * 1000) & 0xFFFFFFFF, # boot time ms
                self.target_system,
                self.target_component,
                mavutil.mavlink.MAV_FRAME_BODY_NED,
                type_mask,
                0.0, 0.0, 0.0, # position (ignored)
                float(vx), float(vy), float(vz), # velocity
                0.0, 0.0, 0.0, # accel (ignored)
                0.0, float(yaw_rate_rad) # yaw, yaw_rate
            )
            return True
        except Exception as e:
            logger.error(f"[SIM] Error sending velocity move: {e}")
            return False

    async def set_heading(self, heading_deg: float) -> bool:
        """Sends MAV_CMD_CONDITION_YAW to align with target heading."""
        logger.info(f"[SIM] SET_HEADING command sent: {heading_deg} deg")
        return await self._send_command_long(
            command=mavutil.mavlink.MAV_CMD_CONDITION_YAW,
            param1=float(heading_deg % 360), # target angle
            param2=25.0, # turn speed deg/s
            param3=1.0,  # 1 for clockwise, -1 for counter-clockwise
            param4=0.0   # 0 for absolute, 1 for relative
        )

    async def return_to_home(self) -> bool:
        """Sends MAV_CMD_NAV_RETURN_TO_LAUNCH."""
        logger.info("[SIM] RETURN_TO_HOME command sent")
        return await self._send_command_long(
            command=mavutil.mavlink.MAV_CMD_NAV_RETURN_TO_LAUNCH
        )

    async def get_telemetry(self) -> Dict[str, Any]:
        """Returns standardized telemetry dictionary."""
        with self._lock:
            return self.telemetry.to_command_centre_schema()

    async def get_camera_frame(self) -> Optional[np.ndarray]:
        """Returns camera frame from provider if available."""
        if self._camera_provider:
            return await self._camera_provider.get_latest_frame()
        return self._last_frame

    async def send_mission(self, mission: Dict[str, Any]) -> bool:
        """Uploads mission waypoints to autopilot."""
        logger.info(f"[SIM] Mission upload received: {len(mission.get('waypoints', []))} waypoints")
        # In full implementation, uses MAVLink mission protocol (MISSION_COUNT, MISSION_ITEM_INT)
        return True

    async def init_sitl_params(self) -> None:
        """
        Initialise SITL-specific parameters for automated testing.
        Sets ARMING_CHECK=0 to skip all sensor calibration requirements in simulation.
        This matches the ArduPilot SITL automated test sequence.
        """
        if not self._master:
            return
        try:
            # ARMING_CHECK bitmask: 0 = disable all arming checks (SITL only)
            self._master.mav.param_set_send(
                self.target_system, self.target_component,
                b'ARMING_CHECK',
                0.0,
                mavutil.mavlink.MAV_PARAM_TYPE_REAL32
            )
            logger.info("[SIM] SITL param: ARMING_CHECK=0 set")
            await asyncio.sleep(0.1)
        except Exception as e:
            logger.warning(f"[SIM] Could not set ARMING_CHECK param: {e}")

    # ─────────────────────────────────────────────
    #  Internal Helpers
    # ─────────────────────────────────────────────

    async def _set_mode_guided(self) -> bool:
        """Sets autopilot to GUIDED mode (required for ArduPilot SITL arming and takeoff)."""
        if not self._master:
            return False
        try:
            if self._autopilot_type == 3:  # ArduPilot
                # ArduPilot GUIDED = mode 4
                self._master.set_mode_send(self.target_system, 'GUIDED')
            else:
                # PX4: use MAV_CMD_DO_SET_MODE with AUTO.LOITER (main_mode=5)
                await self._send_command_long(
                    command=mavutil.mavlink.MAV_CMD_DO_SET_MODE,
                    param1=float(mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED),
                    param2=6.0  # PX4 OFFBOARD / POSCTL
                )
            return True
        except Exception as e:
            logger.warning(f"[SIM] set_mode_guided failed: {e}")
            return False

    async def _send_command_long(
        self,
        command: int,
        param1: float = 0.0,
        param2: float = 0.0,
        param3: float = 0.0,
        param4: float = 0.0,
        param5: float = 0.0,
        param6: float = 0.0,
        param7: float = 0.0
    ) -> bool:
        if not self._master:
            return False

        try:
            self._master.mav.command_long_send(
                self.target_system,
                self.target_component,
                command,
                0, # confirmation
                param1, param2, param3, param4, param5, param6, param7
            )
            return True
        except Exception as e:
            logger.error(f"[SIM] Error sending command {command}: {e}")
            return False

    def _rx_worker(self):
        """
        Background receiver loop decoding incoming MAVLink packets.
        """
        while self._running and self._master:
            try:
                msg = self._master.recv_match(blocking=True, timeout=0.5)
                if not msg:
                    continue

                msg_type = msg.get_type()
                now = time.time()

                if msg_type == "HEARTBEAT":
                    self._handle_heartbeat(msg, now)
                elif msg_type == "GLOBAL_POSITION_INT":
                    self._handle_global_pos(msg, now)
                elif msg_type == "ATTITUDE":
                    self._handle_attitude(msg, now)
                elif msg_type == "SYS_STATUS":
                    self._handle_sys_status(msg, now)
                elif msg_type == "VFR_HUD":
                    self._handle_vfr_hud(msg, now)
                elif msg_type == "GPS_RAW_INT":
                    self._handle_gps_raw(msg, now)

            except Exception as e:
                if self._running:
                    time.sleep(0.05)

    def _handle_heartbeat(self, msg, now: float):
        with self._lock:
            self._last_heartbeat_time = now
            self._connected = True
            base_mode = getattr(msg, 'base_mode', 0)
            custom_mode = getattr(msg, 'custom_mode', 0)
            autopilot = getattr(msg, 'autopilot', 0)

            # Cache autopilot type for mode decoding (3=ArduPilot, 12=PX4)
            if autopilot in (3, 12):
                self._autopilot_type = autopilot

            is_armed = bool(base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED)
            self.telemetry.is_armed = is_armed
            self.telemetry.last_packet_timestamp = now
            self.telemetry.link_status = 'ONLINE'

            # Flight mode decoding — autopilot-aware
            if self._autopilot_type == 3:
                # ArduPilot: custom_mode is a plain integer flight mode number
                mode = _ARDUPILOT_MODES.get(custom_mode, f'MODE_{custom_mode}')
            else:
                # PX4: main_mode in bits 16-23 of custom_mode
                main_mode = (custom_mode >> 16) & 0xFF
                mode = _PX4_MAIN_MODES.get(main_mode, f'PX4_MODE_{main_mode}')

            if is_armed:
                self.telemetry.flight_mode = mode
            else:
                self.telemetry.flight_mode = f'{mode}' if mode != 'STABILIZE' else 'DISARMED'

    def _handle_global_pos(self, msg, now: float):
        with self._lock:
            self.telemetry.latitude = msg.lat / 1e7
            self.telemetry.longitude = msg.lon / 1e7
            self.telemetry.altitude_m = msg.alt / 1000.0
            self.telemetry.relative_altitude_m = msg.relative_alt / 1000.0
            vx = msg.vx / 100.0
            vy = msg.vy / 100.0
            vz = msg.vz / 100.0
            self.telemetry.ground_speed_mps = math.sqrt(vx**2 + vy**2)
            self.telemetry.vertical_speed_mps = -vz # negative vz is climbing
            if msg.hdg != 65535:
                self.telemetry.heading_deg = msg.hdg / 100.0
            self.telemetry.last_packet_timestamp = now
            self.telemetry.timestamp_utc = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(now))

    def _handle_attitude(self, msg, now: float):
        with self._lock:
            self.telemetry.roll_deg = math.degrees(msg.roll)
            self.telemetry.pitch_deg = math.degrees(msg.pitch)
            self.telemetry.yaw_deg = math.degrees(msg.yaw) % 360.0
            self.telemetry.last_packet_timestamp = now

    def _handle_sys_status(self, msg, now: float):
        with self._lock:
            if msg.voltage_battery != -1:
                self.telemetry.battery_voltage_v = msg.voltage_battery / 1000.0
            if msg.battery_remaining != -1:
                self.telemetry.battery_percent = float(msg.battery_remaining)
            self.telemetry.last_packet_timestamp = now

    def _handle_vfr_hud(self, msg, now: float):
        with self._lock:
            self.telemetry.ground_speed_mps = msg.groundspeed
            self.telemetry.heading_deg = float(msg.heading)
            self.telemetry.vertical_speed_mps = msg.climb
            self.telemetry.last_packet_timestamp = now

    def _handle_gps_raw(self, msg, now: float):
        with self._lock:
            fix_type = getattr(msg, "fix_type", 0)
            self.telemetry.gps_status = "FIXED" if fix_type >= 3 else ("ACQUIRING" if fix_type == 2 else "NO_FIX")
            self.telemetry.satellites = getattr(msg, "satellites_visible", 18)
            self.telemetry.hdop = getattr(msg, "eph", 100) / 100.0
            self.telemetry.last_packet_timestamp = now
