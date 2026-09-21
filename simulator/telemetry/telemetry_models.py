"""
PROJECT S.I.G.H.T. — Telemetry Models
Standardized telemetry representations for real-time simulator streaming.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, Any, Optional


@dataclass
class SimulatorTelemetry:
    """
    Standardized live telemetry payload received from genuine simulated UAV.
    """
    timestamp_utc: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    altitude_m: Optional[float] = None
    relative_altitude_m: Optional[float] = None
    ground_speed_mps: Optional[float] = None
    vertical_speed_mps: Optional[float] = None
    heading_deg: Optional[float] = None
    roll_deg: Optional[float] = None
    pitch_deg: Optional[float] = None
    yaw_deg: Optional[float] = None
    battery_percent: Optional[float] = None
    battery_voltage_v: Optional[float] = None
    is_armed: Optional[bool] = None
    flight_mode: Optional[str] = None
    system_status: Optional[str] = None
    gps_status: Optional[str] = None
    satellites: Optional[int] = None
    link_status: Optional[str] = None
    current_waypoint: Optional[int] = None
    total_waypoints: Optional[int] = None
    rssi_dbm: Optional[int] = None
    hdop: Optional[float] = None
    last_packet_timestamp: Optional[float] = None

    def is_stale(self, timeout_sec: float = 3.0) -> bool:
        """Determines if telemetry data is older than timeout threshold."""
        if self.last_packet_timestamp is None:
            return self.latitude is None
        return (time.time() - self.last_packet_timestamp) > timeout_sec

    def to_command_centre_schema(self) -> Dict[str, Any]:
        """
        Converts to the exact TypeScript Telemetry schema required by Command Centre.
        Missing live SITL fields are reported honestly as None / UNKNOWN instead of
        defaulting to fake demo values or doing arithmetic on None.
        """
        stale = self.is_stale()
        if stale:
            return {
                "altitude": None, "speed": None, "heading": None, "headingDegrees": None,
                "relativeAltitude": None,
                "battery": None, "batteryVoltage": None, "gpsStatus": "UNKNOWN",
                "gpsSatellites": None, "hdop": None, "lat": None, "lng": None,
                "flightMode": None, "linkStatus": "LOST", "rssi": None,
                "pitch": None, "roll": None, "yaw": None, "climbRate": None,
                "systemStatus": "STANDBY", "isArmed": None, "timestamp": None,
            }

        headings = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']

        def rounded(value: Optional[float], digits: int) -> Optional[float]:
            return round(value, digits) if value is not None else None

        heading_deg = self.heading_deg
        if heading_deg is None:
            heading_str = None
        else:
            hdg_idx = int(((heading_deg + 22.5) % 360) / 45)
            heading_str = headings[hdg_idx]

        computed_link = self.link_status or "ONLINE"
        computed_system = "WARNING" if self.battery_percent is not None and self.battery_percent < 20.0 else (self.system_status or "UNKNOWN")

        return {
            "altitude": rounded(self.altitude_m, 2),
            "relativeAltitude": rounded(self.relative_altitude_m, 2),
            "speed": rounded(self.ground_speed_mps, 2),
            "heading": heading_str,
            "headingDegrees": rounded(self.heading_deg, 1),
            "battery": rounded(self.battery_percent, 1),
            "batteryVoltage": rounded(self.battery_voltage_v, 2),
            "gpsStatus": self.gps_status or "UNKNOWN",
            "gpsSatellites": self.satellites,
            "hdop": self.hdop,
            "lat": rounded(self.latitude, 6),
            "lng": rounded(self.longitude, 6),
            "flightMode": self.flight_mode,
            "linkStatus": computed_link,
            "rssi": self.rssi_dbm,
            "pitch": rounded(self.pitch_deg, 1),
            "roll": rounded(self.roll_deg, 1),
            "yaw": rounded(self.yaw_deg, 1),
            "climbRate": rounded(self.vertical_speed_mps, 2),
            "systemStatus": computed_system,
            "isArmed": self.is_armed,
            "timestamp": self.timestamp_utc,
        }

    def to_governor_context(self) -> Dict[str, Any]:
        """
        Formats vehicle context consumed by S.I.G.H.T. Core Governor rules.
        """
        return {
            "uav_id": "SIGHT-UAV-01",
            "lat": self.latitude,
            "lng": self.longitude,
            "altitude_m": self.altitude_m,
            "battery_percent": self.battery_percent,
            "is_armed": self.is_armed,
            "flight_mode": self.flight_mode,
            "timestamp_utc": self.timestamp_utc,
            "link_status": self.link_status,
        }
