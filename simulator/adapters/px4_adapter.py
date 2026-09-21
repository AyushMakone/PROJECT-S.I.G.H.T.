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
import queue
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
        self._command_ack: Dict[int, int] = {}
        self._last_command_ack: Optional[int] = None
        self._last_command_message = ""
        self._mission_messages: queue.Queue = queue.Queue()
        self._last_mission_ack: Optional[int] = None
        self._autopilot_type: int = 0  # 0=unknown, 3=ArduPilot, 12=PX4
        self._vehicle_type: Optional[int] = None

        # Telemetry store
        self.telemetry = SimulatorTelemetry()
        self._last_heartbeat_time = 0.0
        self._last_frame: Optional[np.ndarray] = None
        self._camera_provider = None

        # Bounded velocity-setpoint lifetime: ArduPilot Guided mode expects repeated
        # SET_POSITION_TARGET_LOCAL_NED packets while the command is active. We keep
        # the loop finite to avoid leaving the vehicle in continuous motion.
        self._move_duration_s = 5.0
        self._move_interval_s = 0.10
        self._max_velocity_mps = 10.0
        self._max_yaw_rate_deg_s = 180.0

    @property
    def mode_name(self) -> str:
        conn = (self.connection_string or "").lower()
        local_markers = (
            "127.0.0.1",
            "0.0.0.0",
            "localhost",
            "172.30.16.1",
            "172.30.",
            "192.168.",
            "10.",
            "169.254.",
        )
        if any(marker in conn for marker in local_markers):
            return "local"
        return "cloud"

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

    @property
    def autopilot_type(self) -> int:
        return self._autopilot_type

    @property
    def vehicle_type(self) -> Optional[int]:
        return self._vehicle_type

    def set_camera_provider(self, provider):
        """Attaches an optical camera feed provider (e.g., FrameManager)."""
        self._camera_provider = provider

    @staticmethod
    def _udp_input_mode(connection_string: str) -> bool:
        """Return the correct UDP socket mode for the live MAVLink topology.

        ArduPilot/MAVProxy deployments commonly use a single bidirectional UDP socket
        that receives telemetry and sends command replies back to the active remote peer.
        Explicitly bind in input/server mode for `udp:` and `udpin:` endpoints, while
        keeping `udpout:` as a send-only client connection.
        """
        lowered = connection_string.lower()
        if lowered.startswith("udpout:"):
            return False
        if lowered.startswith("udp:") or lowered.startswith("udpin:"):
            return True
        return True

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
            # Explicitly select UDP server/client semantics so the GCS path can both
            # receive telemetry and send commands back through the live MAVProxy bridge.
            input_mode = self._udp_input_mode(self.connection_string)
            self._master = mavutil.mavlink_connection(
                self.connection_string,
                source_system=self.source_system,
                source_component=self.source_component,
                input=input_mode,
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

            logger.warning(f"[SIM] No MAVLink heartbeat received from {self.connection_string}")
            await self.disconnect()
            return False
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
        if not self._master:
            return False
        try:
            if self._autopilot_type == 3:
                self._master.set_mode('LOITER')
                return True
            return await self._send_command_long(
                command=mavutil.mavlink.MAV_CMD_DO_SET_MODE,
                param1=float(mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED),
                param2=5.0
            )
        except Exception as e:
            logger.warning(f"[SIM] set_mode_loiter failed: {e}")
            return False

    def _send_velocity_setpoint(self, vx: float, vy: float, vz: float, yaw_rate: float) -> bool:
        """Send a BODY_NED velocity + yaw-rate setpoint using SET_POSITION_TARGET_LOCAL_NED."""
        if not self._master:
            return False

        try:
            # Ignore position, acceleration/force and absolute yaw.
            # # Keep vx/vy/vz and yaw_rate active.
            # # 0x05C7 = X/Y/Z + AX/AY/AZ + YAW ignored; YAW_RATE enabled.
            type_mask = 0x05C7
            yaw_rate_rad = math.radians(float(yaw_rate))

            with self._lock:
                self._master.mav.set_position_target_local_ned_send(
                    int(time.time() * 1000) & 0xFFFFFFFF,
                    self.target_system,
                    self.target_component,
                    mavutil.mavlink.MAV_FRAME_BODY_NED,
                    type_mask,
                    0.0, 0.0, 0.0,
                    float(vx), float(vy), float(vz),
                    0.0, 0.0, 0.0,
                    0.0, float(yaw_rate_rad)
                )
            return True
        except Exception as e:
            logger.error(f"[SIM] Error sending velocity move: {e}")
            return False

    async def move(self, vx: float, vy: float, vz: float, yaw_rate: float = 0.0) -> bool:
        """
        Send a bounded BODY_NED velocity setpoint for ArduPilot Guided mode.

        ArduCopter expects repeated SET_POSITION_TARGET_LOCAL_NED commands while the
        velocity target is active. A single packet is not sufficient to move the
        vehicle reliably. We therefore emit a short pulse of velocity updates for a
        bounded lifetime and end with an explicit zero-velocity hold/stop packet.

        vx: forward (m/s), vy: right (m/s), vz: down (m/s, negative is climb)
        """
        if not self._master:
            return False

        try:
            vx_f = float(vx)
            vy_f = float(vy)
            vz_f = float(vz)
            yaw_rate_f = float(yaw_rate)
        except (TypeError, ValueError):
            logger.warning("[SIM] move() received non-numeric velocity arguments")
            return False

        values = (vx_f, vy_f, vz_f, yaw_rate_f)
        if not all(math.isfinite(v) for v in values):
            logger.warning("[SIM] move() received non-finite velocity values")
            return False

        max_vel = self._max_velocity_mps
        max_yaw = self._max_yaw_rate_deg_s
        if any(abs(v) > max_vel for v in (vx_f, vy_f, vz_f)):
            logger.warning(
                "[SIM] move() rejected absurd velocity command: vx=%s vy=%s vz=%s (max %.1f m/s)",
                vx_f, vy_f, vz_f, max_vel,
            )
            return False
        if abs(yaw_rate_f) > max_yaw:
            logger.warning(
                "[SIM] move() rejected absurd yaw rate: %.2f deg/s (max %.1f deg/s)",
                yaw_rate_f, max_yaw,
            )
            return False

        duration_s = self._move_duration_s
        if all(abs(v) <= 1e-9 for v in (vx_f, vy_f, vz_f, yaw_rate_f)):
            duration_s = 0.25

        deadline = time.monotonic() + duration_s
        while time.monotonic() < deadline:
            if not self._send_velocity_setpoint(vx_f, vy_f, vz_f, yaw_rate_f):
                return False
            await asyncio.sleep(self._move_interval_s)

        # Explicit stop/hold command after the bounded lifetime so the vehicle does
        # not continue drifting under stale velocity data.
        self._send_velocity_setpoint(0.0, 0.0, 0.0, 0.0)
        return True

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
        if not self.is_connected:
            return {
                "connected": False, "lat": None, "lng": None, "altitude": None,
                "speed": None, "headingDegrees": None, "battery": None,
                "linkStatus": "LOST",
                "systemStatus": "STANDBY",
                "isArmed": None,
                "flightMode": None,
                "timestamp": None,
            }
        with self._lock:
            return self.telemetry.to_command_centre_schema()

    async def get_camera_frame(self) -> Optional[np.ndarray]:
        """Returns camera frame from provider if available."""
        if self._camera_provider:
            return await self._camera_provider.get_latest_frame()
        return self._last_frame

    async def send_mission(self, mission: Dict[str, Any]) -> bool:
        """Upload global-relative waypoints using the MAVLink mission protocol."""
        if not self._master or not self.is_connected:
            self._last_mission_ack = None
            return False

        waypoints = mission.get("waypoints", [])
        if not waypoints:
            self._last_mission_ack = None
            return False

        while not self._mission_messages.empty():
            try:
                self._mission_messages.get_nowait()
            except queue.Empty:
                break

        try:
            with self._lock:
                self._master.mav.mission_clear_all_send(self.target_system, self.target_component, 0)
                self._master.mav.mission_count_send(
                    self.target_system, self.target_component, len(waypoints), 0
                )

            for expected_seq in range(len(waypoints)):
                request = await self._wait_for_mission_message(timeout=5.0)
                if request is None or request.get_type() not in ("MISSION_REQUEST_INT", "MISSION_REQUEST"):
                    self._last_mission_ack = None
                    return False
                sequence = int(getattr(request, "seq", expected_seq))
                if sequence != expected_seq:
                    self._last_mission_ack = None
                    return False
                waypoint = waypoints[sequence]
                lat = int(round(float(waypoint["lat"]) * 10_000_000))
                lon_value = waypoint.get("lon", waypoint.get("lng"))
                lon = int(round(float(lon_value) * 10_000_000))
                altitude = float(waypoint["altitude"])
                with self._lock:
                    self._master.mav.mission_item_int_send(
                        self.target_system, self.target_component, sequence,
                        mavutil.mavlink.MAV_FRAME_GLOBAL_RELATIVE_ALT_INT,
                        mavutil.mavlink.MAV_CMD_NAV_WAYPOINT,
                        1 if sequence == 0 else 0, 1,
                        float(waypoint.get("acceptanceRadius", 10.0)), 0.0, 0.0, 0.0,
                        lat, lon, altitude
                    )

            ack = await self._wait_for_mission_message(timeout=5.0)
            self._last_mission_ack = int(getattr(ack, "type", -1)) if ack and ack.get_type() == "MISSION_ACK" else None
            return self._last_mission_ack == mavutil.mavlink.MAV_MISSION_ACCEPTED
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            logger.warning("[SIM] Mission upload failed: %s", exc)
            self._last_mission_ack = None
            return False

    @property
    def last_command_ack(self) -> Optional[int]:
        return self._last_command_ack

    @property
    def last_command_message(self) -> str:
        return self._last_command_message

    @property
    def last_mission_ack(self) -> Optional[int]:
        return self._last_mission_ack

    async def _wait_for_mission_message(self, timeout: float) -> Optional[Any]:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                return self._mission_messages.get_nowait()
            except queue.Empty:
                await asyncio.sleep(0.05)
        return None

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
                self._master.set_mode('GUIDED')
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
            with self._lock:
                self._command_ack.pop(command, None)
                self._last_command_ack = None
                self._last_command_message = ""
            self._master.mav.command_long_send(
                self.target_system,
                self.target_component,
                command,
                0, # confirmation
                param1, param2, param3, param4, param5, param6, param7
            )
            deadline = time.time() + 3.0
            while time.time() < deadline:
                with self._lock:
                    result = self._command_ack.get(command)
                if result is not None:
                    accepted = result in (
                        mavutil.mavlink.MAV_RESULT_ACCEPTED,
                        mavutil.mavlink.MAV_RESULT_IN_PROGRESS,
                    )
                    if not accepted:
                        logger.warning("[SIM] MAVLink command %s rejected with result %s", command, result)
                    self._last_command_ack = result
                    self._last_command_message = f"MAV_RESULT_{result}"
                    return accepted
                await asyncio.sleep(0.05)
            logger.warning("[SIM] MAVLink command %s timed out waiting for COMMAND_ACK", command)
            self._last_command_ack = None
            self._last_command_message = "No COMMAND_ACK received before timeout"
            return False
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
                elif msg_type == "COMMAND_ACK":
                    self._handle_command_ack(msg)
                elif msg_type in ("MISSION_REQUEST_INT", "MISSION_REQUEST", "MISSION_ACK"):
                    self._mission_messages.put(msg)

            except Exception as e:
                if self._running:
                    time.sleep(0.05)

    def _handle_heartbeat(self, msg, now: float):
        with self._lock:
            self._last_heartbeat_time = now
            self._connected = True
            self.target_system = int(msg.get_srcSystem())
            self.target_component = int(msg.get_srcComponent())
            base_mode = getattr(msg, 'base_mode', 0)
            custom_mode = getattr(msg, 'custom_mode', 0)
            autopilot = getattr(msg, 'autopilot', 0)
            self._vehicle_type = getattr(msg, 'type', None)

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
            satellites = getattr(msg, "satellites_visible", -1)
            eph = getattr(msg, "eph", -1)
            self.telemetry.satellites = satellites if satellites >= 0 else None
            self.telemetry.hdop = eph / 100.0 if eph >= 0 else None
            self.telemetry.last_packet_timestamp = now

    def _handle_command_ack(self, msg) -> None:
        with self._lock:
            self._command_ack[int(msg.command)] = int(msg.result)
