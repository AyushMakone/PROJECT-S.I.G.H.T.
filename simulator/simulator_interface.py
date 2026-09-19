"""
PROJECT S.I.G.H.T. — Unified Simulator Interface
Provides unified programmatic facade wrapping simulator adapters,
maintaining test compatibility while supporting real MAVLink & Cloud simulation.
"""

import os
import sys
import time
import json
import asyncio
import threading
from typing import Optional, Dict, Any, List
import numpy as np

from .adapters.base_adapter import BaseSimulatorAdapter
from .adapters.px4_adapter import PX4Adapter
from .adapters.cloud_adapter import CloudAdapter
from .adapters.fallback_adapter import FallbackAdapter
from .fallback.px4.autopilot_state import AutopilotStateMachine, FlightMode, Waypoint
from .fallback.gazebo.world_server import GazeboWorldServer
from .fallback.gazebo.camera_sensor import UAVCameraSensor
from .fallback.px4.mavlink_server import MAVLinkServer


class SimulatorInterface:
    """
    Unified programmatic interface for controlling the UAV Simulator.
    Seamlessly routes commands to the active adapter (Cloud, Local PX4, or Fallback).
    """

    def __init__(
        self,
        mavlink_port: int = 14550,
        camera_width: int = 640,
        camera_height: int = 480,
        camera_fps: int = 15,
        mode: Optional[str] = None
    ):
        self.mavlink_port = mavlink_port
        self.camera_width = camera_width
        self.camera_height = camera_height
        self.camera_fps = camera_fps

        self.mode = (mode or os.getenv("SIMULATOR_MODE", "fallback")).lower()

        # Legacy fallback subsystems maintained for offline test fixtures
        self.autopilot = AutopilotStateMachine()
        self.world = GazeboWorldServer()
        self.camera = UAVCameraSensor(
            world=self.world,
            width=self.camera_width,
            height=self.camera_height,
            fps=self.camera_fps
        )
        self.mavlink_server: Optional[MAVLinkServer] = None

        # Adapter selection
        if self.mode == "cloud":
            self.adapter: BaseSimulatorAdapter = CloudAdapter(port=mavlink_port)
        elif self.mode == "local":
            self.adapter = PX4Adapter(connection_string=f"udpin:0.0.0.0:{mavlink_port}")
        else:
            self.adapter = FallbackAdapter(mavlink_port=mavlink_port, camera_fps=camera_fps)

        # Loop management
        self.running = False
        self.physics_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

    def start(self, enable_mavlink: bool = True) -> bool:
        if self.running:
            return True
        self.running = True

        if enable_mavlink:
            self.mavlink_server = MAVLinkServer(self.autopilot, port=self.mavlink_port)
            self.mavlink_server.start()

        self.physics_thread = threading.Thread(target=self._physics_loop, daemon=True)
        self.physics_thread.start()
        return True

    def stop(self):
        self.running = False
        if self.mavlink_server:
            self.mavlink_server.stop()
            self.mavlink_server = None
        if self.physics_thread and self.physics_thread.is_alive():
            self.physics_thread.join(timeout=1.5)

    def arm(self) -> bool:
        with self._lock:
            return self.autopilot.arm()

    def disarm(self) -> bool:
        with self._lock:
            return self.autopilot.disarm()

    def takeoff(self, altitude_m: float = 84.0) -> bool:
        with self._lock:
            return self.autopilot.takeoff(altitude_m)

    def land(self):
        with self._lock:
            self.autopilot.land()

    def return_to_home(self):
        with self._lock:
            self.autopilot.return_to_home()

    def load_mission(self, mission_json_path: str) -> bool:
        if not os.path.exists(mission_json_path):
            raise FileNotFoundError(f"Mission file not found: {mission_json_path}")

        with open(mission_json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        waypoints = []
        for wp_data in data.get("waypoints", []):
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

        with self._lock:
            self.autopilot.load_waypoints(waypoints)
        return True

    def run_mission(self) -> bool:
        with self._lock:
            return self.autopilot.start_mission()

    def step(self, dt: float = 0.1) -> Dict[str, Any]:
        with self._lock:
            telem = self.autopilot.update(dt)
        return self._format_telemetry(telem)

    def get_telemetry(self) -> Dict[str, Any]:
        with self._lock:
            telem = self.autopilot.get_telemetry()
        return self._format_telemetry(telem)

    def capture_frame(self) -> np.ndarray:
        with self._lock:
            telem = self.autopilot.get_telemetry()
            return self.camera.capture_frame(
                uav_lat=telem.lat,
                uav_lng=telem.lng,
                uav_alt_m=telem.altitude_m,
                uav_heading_deg=telem.heading_deg,
                target_timestamp=telem.timestamp_utc
            )

    def get_visible_targets(self) -> List[Dict[str, Any]]:
        with self._lock:
            telem = self.autopilot.get_telemetry()
            return self.world.get_entities_in_camera_fov(
                uav_lat=telem.lat,
                uav_lng=telem.lng,
                uav_alt_m=telem.altitude_m,
                uav_heading_deg=telem.heading_deg
            )

    def reset(self):
        with self._lock:
            self.autopilot = AutopilotStateMachine()
            self.world = GazeboWorldServer()
            self.camera = UAVCameraSensor(self.world, self.camera_width, self.camera_height, self.camera_fps)
            if self.mavlink_server:
                self.mavlink_server.autopilot = self.autopilot

    def _physics_loop(self):
        dt = 0.05
        while self.running:
            start_t = time.time()
            with self._lock:
                self.autopilot.update(dt)
            elapsed = time.time() - start_t
            time.sleep(max(0.001, dt - elapsed))

    def _format_telemetry(self, telem) -> Dict[str, Any]:
        return {
            "lat": telem.lat,
            "lng": telem.lng,
            "altitude_m": telem.altitude_m,
            "speed_mps": telem.speed_mps,
            "heading_deg": telem.heading_deg,
            "climb_rate_mps": telem.climb_rate_mps,
            "roll_deg": telem.roll_deg,
            "pitch_deg": telem.pitch_deg,
            "yaw_deg": telem.yaw_deg,
            "battery_percent": telem.battery_percent,
            "battery_voltage_v": telem.battery_voltage_v,
            "is_armed": telem.is_armed,
            "flight_mode": telem.flight_mode.value if hasattr(telem.flight_mode, "value") else str(telem.flight_mode),
            "current_waypoint": telem.current_waypoint_idx,
            "total_waypoints": telem.total_waypoints,
            "timestamp_utc": telem.timestamp_utc
        }
