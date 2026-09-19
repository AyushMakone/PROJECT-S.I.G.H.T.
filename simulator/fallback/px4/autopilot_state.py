"""
PROJECT S.I.G.H.T. - Virtual UAV Flight State Machine & Kinematics
Implements 6-DOF kinematics, waypoint tracking, flight modes, and battery discharge.
"""

import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple, Dict, Any

class FlightMode(str, Enum):
    MANUAL = "MANUAL"
    ARMING = "ARMING"
    ARMED = "ARMED"
    TAKEOFF = "TAKEOFF"
    AUTO_MISSION = "AUTO_MISSION"
    LOITER = "LOITER"
    RETURN_TO_HOME = "RETURN_TO_HOME"
    LANDING = "LANDING"
    LANDED = "LANDED"
    DISARMED = "DISARMED"

@dataclass
class Waypoint:
    id: str
    name: str
    lat: float = 0.0
    lng: float = 0.0
    altitude_m: float = 0.0
    speed_mps: float = 12.0
    acceptance_radius_m: float = 5.0
    is_priority_zone: bool = False

@dataclass
class UAVTelemetry:
    lat: float
    lng: float
    altitude_m: float
    speed_mps: float
    heading_deg: float
    climb_rate_mps: float
    roll_deg: float
    pitch_deg: float
    yaw_deg: float
    battery_percent: float
    battery_voltage_v: float
    is_armed: bool
    flight_mode: FlightMode
    current_waypoint_idx: int
    total_waypoints: int
    timestamp_utc: str

class AutopilotStateMachine:
    """
    Virtual UAV Autopilot with 6-DOF kinematics and navigation.
    """
    def __init__(self, home_lat: float = 34.0522, home_lng: float = -117.8247, home_alt: float = 0.0):
        self.home_lat = home_lat
        self.home_lng = home_lng
        self.home_alt = home_alt

        # Current kinematic state
        self.lat = home_lat
        self.lng = home_lng
        self.altitude_m = home_alt
        self.speed_mps = 0.0
        self.heading_deg = 45.0
        self.climb_rate_mps = 0.0
        self.roll_deg = 0.0
        self.pitch_deg = 0.0
        self.yaw_deg = 45.0

        # System state
        self.is_armed = False
        self.flight_mode = FlightMode.DISARMED
        self.battery_percent = 100.0
        self.battery_voltage_v = 25.2 # 6S fully charged

        # Mission navigation
        self.waypoints: List[Waypoint] = []
        self.current_wp_idx: int = 0
        self.target_altitude_m: float = 0.0
        self.target_speed_mps: float = 12.0

        # Timing
        self.last_update_time = time.time()
        self.mission_complete_callback = None

    def arm(self) -> bool:
        if self.flight_mode in [FlightMode.DISARMED, FlightMode.LANDED]:
            self.is_armed = True
            self.flight_mode = FlightMode.ARMED
            return True
        return False

    def disarm(self) -> bool:
        if self.altitude_m <= 0.5:
            self.is_armed = False
            self.flight_mode = FlightMode.DISARMED
            self.speed_mps = 0.0
            self.climb_rate_mps = 0.0
            return True
        return False

    def takeoff(self, target_altitude: float = 84.0) -> bool:
        if not self.is_armed:
            self.arm()
        self.flight_mode = FlightMode.TAKEOFF
        self.target_altitude_m = target_altitude
        return True

    def load_waypoints(self, waypoints: List[Waypoint]):
        self.waypoints = waypoints
        self.current_wp_idx = 0

    def start_mission(self) -> bool:
        if not self.waypoints:
            return False
        if not self.is_armed:
            self.arm()
        if self.altitude_m < 5.0:
            self.takeoff(self.waypoints[0].altitude_m or 84.0)
        self.flight_mode = FlightMode.AUTO_MISSION
        return True

    def return_to_home(self):
        self.flight_mode = FlightMode.RETURN_TO_HOME
        self.target_altitude_m = 80.0

    def land(self):
        self.flight_mode = FlightMode.LANDING
        self.target_speed_mps = 0.0

    def update(self, dt: Optional[float] = None) -> UAVTelemetry:
        """
        Main physics and navigation step.
        """
        now = time.time()
        if dt is None:
            dt = max(0.01, min(1.0, now - self.last_update_time))
        self.last_update_time = now

        # Battery consumption: base idle + motor power proportional to speed and climb
        discharge_rate = 0.008 if not self.is_armed else (0.04 + (self.speed_mps / 20.0) * 0.03)
        self.battery_percent = max(0.0, self.battery_percent - (discharge_rate * dt))
        self.battery_voltage_v = round(21.0 + (self.battery_percent / 100.0) * 4.2, 2)

        # Handle flight state transitions
        if self.flight_mode == FlightMode.TAKEOFF:
            self._handle_takeoff(dt)
        elif self.flight_mode == FlightMode.AUTO_MISSION:
            self._handle_waypoint_nav(dt)
        elif self.flight_mode == FlightMode.RETURN_TO_HOME:
            self._handle_rth(dt)
        elif self.flight_mode == FlightMode.LANDING:
            self._handle_landing(dt)
        elif self.flight_mode == FlightMode.LOITER:
            self._handle_loiter(dt)

        return self.get_telemetry()

    def _handle_takeoff(self, dt: float):
        climb_speed = 3.5 # m/s
        self.climb_rate_mps = climb_speed
        self.altitude_m += climb_speed * dt
        self.pitch_deg = 4.0
        self.roll_deg = 0.0

        if self.altitude_m >= self.target_altitude_m:
            self.altitude_m = self.target_altitude_m
            self.climb_rate_mps = 0.0
            self.pitch_deg = 0.0
            if self.waypoints:
                self.flight_mode = FlightMode.AUTO_MISSION
            else:
                self.flight_mode = FlightMode.LOITER

    def _handle_waypoint_nav(self, dt: float):
        if not self.waypoints or self.current_wp_idx >= len(self.waypoints):
            self.return_to_home()
            return

        wp = self.waypoints[self.current_wp_idx]
        dist_m = self._distance_meters(self.lat, self.lng, wp.lat, wp.lng)
        target_bearing = self._bearing_degrees(self.lat, self.lng, wp.lat, wp.lng)

        # Turn smoothly toward bearing
        angle_diff = (target_bearing - self.heading_deg + 180) % 360 - 180
        turn_rate = max(-45.0, min(45.0, angle_diff * 2.0))
        self.heading_deg = (self.heading_deg + turn_rate * dt) % 360
        self.yaw_deg = self.heading_deg
        self.roll_deg = max(-20.0, min(20.0, turn_rate * 0.5))

        # Advance along heading
        self.speed_mps = min(wp.speed_mps, self.speed_mps + 2.0 * dt)
        dist_step = self.speed_mps * dt

        # Convert meters to lat/lng delta
        lat_step = (dist_step * math.cos(math.radians(self.heading_deg))) / 111139.0
        lng_step = (dist_step * math.sin(math.radians(self.heading_deg))) / (111139.0 * math.cos(math.radians(self.lat)))
        self.lat += lat_step
        self.lng += lng_step

        # Vertical navigation
        alt_err = wp.altitude_m - self.altitude_m
        climb = max(-3.0, min(3.0, alt_err))
        self.climb_rate_mps = climb
        self.altitude_m += climb * dt
        self.pitch_deg = max(-10.0, min(10.0, climb * 2.0))

        # Check waypoint acceptance
        if dist_m <= wp.acceptance_radius_m:
            self.current_wp_idx += 1
            if self.current_wp_idx >= len(self.waypoints):
                self.return_to_home()

    def _handle_rth(self, dt: float):
        dist_home = self._distance_meters(self.lat, self.lng, self.home_lat, self.home_lng)
        if dist_home <= 8.0:
            self.land()
            return

        bearing = self._bearing_degrees(self.lat, self.lng, self.home_lat, self.home_lng)
        self.heading_deg = bearing
        self.yaw_deg = bearing
        self.speed_mps = 14.0

        dist_step = self.speed_mps * dt
        self.lat += (dist_step * math.cos(math.radians(bearing))) / 111139.0
        self.lng += (dist_step * math.sin(math.radians(bearing))) / (111139.0 * math.cos(math.radians(self.lat)))

    def _handle_landing(self, dt: float):
        self.speed_mps = max(0.0, self.speed_mps - 4.0 * dt)
        descent_speed = 2.0 # m/s
        self.climb_rate_mps = -descent_speed
        self.altitude_m -= descent_speed * dt
        self.pitch_deg = -2.0
        self.roll_deg = 0.0

        if self.altitude_m <= 0.0:
            self.altitude_m = 0.0
            self.climb_rate_mps = 0.0
            self.speed_mps = 0.0
            self.pitch_deg = 0.0
            self.flight_mode = FlightMode.LANDED
            self.disarm()

    def _handle_loiter(self, dt: float):
        # Loiter in circle with radius ~30m
        omega = 0.15 # rad/s
        self.heading_deg = (self.heading_deg + math.degrees(omega) * dt) % 360
        self.yaw_deg = self.heading_deg
        self.speed_mps = 8.0
        self.climb_rate_mps = 0.0
        self.roll_deg = 8.0

        dist_step = self.speed_mps * dt
        self.lat += (dist_step * math.cos(math.radians(self.heading_deg))) / 111139.0
        self.lng += (dist_step * math.sin(math.radians(self.heading_deg))) / (111139.0 * math.cos(math.radians(self.lat)))

    def get_telemetry(self) -> UAVTelemetry:
        now_str = time.strftime("%H:%M:%S UTC", time.gmtime())
        return UAVTelemetry(
            lat=round(self.lat, 6),
            lng=round(self.lng, 6),
            altitude_m=round(self.altitude_m, 1),
            speed_mps=round(self.speed_mps, 1),
            heading_deg=round(self.heading_deg, 1),
            climb_rate_mps=round(self.climb_rate_mps, 1),
            roll_deg=round(self.roll_deg, 1),
            pitch_deg=round(self.pitch_deg, 1),
            yaw_deg=round(self.yaw_deg, 1),
            battery_percent=round(self.battery_percent, 1),
            battery_voltage_v=round(self.battery_voltage_v, 2),
            is_armed=self.is_armed,
            flight_mode=self.flight_mode,
            current_waypoint_idx=self.current_wp_idx,
            total_waypoints=len(self.waypoints),
            timestamp_utc=now_str
        )

    @staticmethod
    def _distance_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        # Haversine distance in meters
        R = 6371000.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lng2 - lng1)
        a = math.sin(dphi / 2.0)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2.0)**2
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return R * c

    @staticmethod
    def _bearing_degrees(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        dlam = math.radians(lng2 - lng1)
        y = math.sin(dlam) * math.cos(phi2)
        x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlam)
        bearing = math.degrees(math.atan2(y, x))
        return (bearing + 360.0) % 360.0
