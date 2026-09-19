"""
PROJECT S.I.G.H.T. — Fallback Simulator Adapter
WARNING: FALLBACK / DEVELOPMENT ONLY — NOT THE PRIMARY FLIGHT SIMULATOR.
Wraps the legacy in-memory kinematics state machine for offline testing.
"""

import time
import asyncio
import logging
from typing import Dict, Any, Optional
import numpy as np

from .base_adapter import BaseSimulatorAdapter
from ..telemetry.telemetry_models import SimulatorTelemetry

# Import from fallback directory
from ..fallback.px4.autopilot_state import AutopilotStateMachine, FlightMode, Waypoint
from ..fallback.gazebo.world_server import GazeboWorldServer
from ..fallback.gazebo.camera_sensor import UAVCameraSensor

logger = logging.getLogger("SIGHT.FallbackAdapter")


class FallbackAdapter(BaseSimulatorAdapter):
    """
    Offline development fallback simulator adapter.
    Explicitly marked: NOT THE PRIMARY FLIGHT SIMULATOR.
    """

    def __init__(self, mavlink_port: int = 14550, camera_fps: int = 15):
        logger.warning("================================================================")
        logger.warning("[SIM] NOTICE: Initializing FallbackAdapter.")
        logger.warning("[SIM] FALLBACK / DEVELOPMENT ONLY — NOT THE PRIMARY FLIGHT SIMULATOR")
        logger.warning("================================================================")

        self.autopilot = AutopilotStateMachine()
        self.world = GazeboWorldServer()
        self.camera = UAVCameraSensor(world=self.world, fps=camera_fps)
        self._connected = False
        self._running = False
        self._loop_task: Optional[asyncio.Task] = None

    @property
    def mode_name(self) -> str:
        return "fallback"

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def is_armed(self) -> bool:
        return self.autopilot.is_armed

    @property
    def flight_mode(self) -> str:
        return self.autopilot.flight_mode.value

    async def connect(self) -> bool:
        self._connected = True
        self._running = True
        # Start async physics stepping loop
        if self._loop_task is None or self._loop_task.done():
            self._loop_task = asyncio.create_task(self._physics_loop())
        logger.info("[SIM] FallbackAdapter connected (in-memory dev engine active).")
        return True

    async def disconnect(self) -> None:
        self._running = False
        self._connected = False
        if self._loop_task:
            self._loop_task.cancel()
            self._loop_task = None
        logger.info("[SIM] FallbackAdapter disconnected.")

    async def arm(self) -> bool:
        logger.info("[SIM] [FALLBACK] ARM command sent")
        return self.autopilot.arm()

    async def disarm(self) -> bool:
        logger.info("[SIM] [FALLBACK] DISARM command sent")
        return self.autopilot.disarm()

    async def takeoff(self, altitude: float = 10.0) -> bool:
        logger.info(f"[SIM] [FALLBACK] TAKEOFF command sent (altitude={altitude}m)")
        return self.autopilot.takeoff(target_altitude=altitude)

    async def land(self) -> bool:
        logger.info("[SIM] [FALLBACK] LAND command sent")
        self.autopilot.land()
        return True

    async def hover(self) -> bool:
        logger.info("[SIM] [FALLBACK] HOVER command sent")
        self.autopilot.flight_mode = FlightMode.LOITER
        self.autopilot.speed_mps = 0.0
        self.autopilot.climb_rate_mps = 0.0
        return True

    async def move(self, vx: float, vy: float, vz: float, yaw_rate: float = 0.0) -> bool:
        # Move command updates velocity
        speed = float(np.sqrt(vx**2 + vy**2))
        self.autopilot.speed_mps = speed
        self.autopilot.climb_rate_mps = -float(vz)
        if speed > 0.1:
            # calculate heading in degrees from vx, vy
            import math
            self.autopilot.heading_deg = math.degrees(math.atan2(vy, vx)) % 360
            self.autopilot.yaw_deg = self.autopilot.heading_deg
        return True

    async def set_heading(self, heading_deg: float) -> bool:
        self.autopilot.heading_deg = float(heading_deg % 360)
        self.autopilot.yaw_deg = self.autopilot.heading_deg
        return True

    async def return_to_home(self) -> bool:
        self.autopilot.return_to_home()
        return True

    async def get_telemetry(self) -> Dict[str, Any]:
        telem = self.autopilot.get_telemetry()
        headings = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
        hdg_idx = int(((telem.heading_deg + 22.5) % 360) / 45)
        heading_str = headings[hdg_idx]

        return {
            "altitude": round(telem.altitude_m, 2),
            "speed": round(telem.speed_mps, 2),
            "heading": heading_str,
            "headingDegrees": round(telem.heading_deg, 1),
            "battery": round(telem.battery_percent, 1),
            "batteryVoltage": round(telem.battery_voltage_v, 2),
            "gpsStatus": "FIXED" if telem.is_armed or telem.altitude_m > 0 else "ACQUIRING",
            "gpsSatellites": 18,
            "hdop": 0.75,
            "lat": round(telem.lat, 6),
            "lng": round(telem.lng, 6),
            "flightMode": telem.flight_mode.value,
            "linkStatus": "ONLINE",
            "rssi": -65,
            "pitch": round(telem.pitch_deg, 1),
            "roll": round(telem.roll_deg, 1),
            "yaw": round(telem.yaw_deg, 1),
            "climbRate": round(telem.climb_rate_mps, 2),
            "systemStatus": "WARNING" if telem.battery_percent < 20 else "ONLINE",
            "isArmed": telem.is_armed,
            "timestamp": telem.timestamp_utc,
            "isFallback": True
        }

    async def get_camera_frame(self) -> Optional[np.ndarray]:
        telem = self.autopilot.get_telemetry()
        return self.camera.capture_frame(
            uav_lat=telem.lat,
            uav_lng=telem.lng,
            uav_alt_m=telem.altitude_m,
            uav_heading_deg=telem.heading_deg,
            target_timestamp=telem.timestamp_utc
        )

    async def send_mission(self, mission: Dict[str, Any]) -> bool:
        waypoints = []
        for wp_data in mission.get("waypoints", []):
            wp = Waypoint(
                id=wp_data.get("id", ""),
                name=wp_data.get("name", ""),
                lat=float(wp_data.get("lat", 0.0)),
                lng=float(wp_data.get("lng", 0.0)),
                altitude_m=float(wp_data.get("altitude_m", 80.0)),
                speed_mps=float(wp_data.get("speed_mps", 12.0)),
                acceptance_radius_m=float(wp_data.get("acceptance_radius_m", 8.0)),
                is_priority_zone=bool(wp_data.get("is_priority_zone", False))
            )
            waypoints.append(wp)
        self.autopilot.load_waypoints(waypoints)
        return True

    async def _physics_loop(self):
        dt = 0.05
        while self._running:
            self.autopilot.update(dt)
            await asyncio.sleep(dt)
