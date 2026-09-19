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
    timestamp_utc: str = field(default_factory=lambda: time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()))
    latitude: float = 34.0522
    longitude: float = -117.8247
    altitude_m: float = 0.0
    relative_altitude_m: float = 0.0
    ground_speed_mps: float = 0.0
    vertical_speed_mps: float = 0.0
    heading_deg: float = 0.0
    roll_deg: float = 0.0
    pitch_deg: float = 0.0
    yaw_deg: float = 0.0
    battery_percent: float = 100.0
    battery_voltage_v: float = 24.6
    is_armed: bool = False
    flight_mode: str = "DISARMED"
    system_status: str = "ONLINE"
    gps_status: str = "FIXED"
    satellites: int = 18
    link_status: str = "ONLINE"
    current_waypoint: int = 0
    total_waypoints: int = 0
    rssi_dbm: int = -65
    hdop: float = 0.8
    last_packet_timestamp: float = field(default_factory=time.time)

    def is_stale(self, timeout_sec: float = 3.0) -> bool:
        """Determines if telemetry data is older than timeout threshold."""
        return (time.time() - self.last_packet_timestamp) > timeout_sec

    def to_command_centre_schema(self) -> Dict[str, Any]:
        """
        Converts to the exact TypeScript Telemetry schema required by Command Centre:
        {
          altitude: number,
          speed: number,
          heading: string,
          headingDegrees: number,
          battery: number,
          batteryVoltage: number,
          gpsStatus: 'FIXED' | 'NO_FIX' | 'ACQUIRING',
          gpsSatellites: number,
          hdop: number,
          lat: number,
          lng: number,
          flightMode: string,
          linkStatus: 'ONLINE' | 'DEGRADED' | 'LOST',
          rssi: number,
          pitch: number,
          roll: number,
          yaw: number,
          climbRate: number,
          systemStatus: 'ONLINE' | 'STANDBY' | 'WARNING'
        }
        """
        headings = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW']
        hdg_idx = int(((self.heading_deg + 22.5) % 360) / 45)
        heading_str = headings[hdg_idx]

        stale = self.is_stale()
        computed_link = "LOST" if stale else self.link_status
        computed_system = "WARNING" if (stale or self.battery_percent < 20.0) else self.system_status

        return {
            "altitude": round(self.altitude_m, 2),
            "speed": round(self.ground_speed_mps, 2),
            "heading": heading_str,
            "headingDegrees": round(self.heading_deg, 1),
            "battery": round(self.battery_percent, 1),
            "batteryVoltage": round(self.battery_voltage_v, 2),
            "gpsStatus": "NO_FIX" if stale else self.gps_status,
            "gpsSatellites": self.satellites,
            "hdop": self.hdop,
            "lat": round(self.latitude, 6),
            "lng": round(self.longitude, 6),
            "flightMode": self.flight_mode,
            "linkStatus": computed_link,
            "rssi": self.rssi_dbm,
            "pitch": round(self.pitch_deg, 1),
            "roll": round(self.roll_deg, 1),
            "yaw": round(self.yaw_deg, 1),
            "climbRate": round(self.vertical_speed_mps, 2),
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
