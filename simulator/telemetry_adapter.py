"""
PROJECT S.I.G.H.T. - Telemetry Adapter
Converts simulator kinematics into standardized telemetry schemas
for S.I.G.H.T. Core, Communication Controller, and Ground Command Centre.
"""

from typing import Dict, Any

class TelemetryAdapter:
    """
    Standardizes simulator telemetry into GCS and S.I.G.H.T. Governor schemas.
    """
    @staticmethod
    def to_command_centre_schema(raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formats into the exact TypeScript Telemetry interface of the Command Centre:
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
        heading_deg = raw.get("heading_deg")
        if heading_deg is None:
            heading_str = None
        else:
            hdg_idx = int(((heading_deg + 22.5) % 360) / 45)
            heading_str = headings[hdg_idx]

        is_armed = raw.get("is_armed")
        batt = raw.get("battery_percent")

        return {
            "altitude": raw.get("altitude_m"),
            "speed": raw.get("speed_mps"),
            "heading": heading_str,
            "headingDegrees": heading_deg,
            "battery": batt,
            "batteryVoltage": raw.get("battery_voltage_v"),
            "gpsStatus": raw.get("gps_status") or "UNKNOWN",
            "gpsSatellites": raw.get("gps_satellites"),
            "hdop": raw.get("hdop"),
            "lat": raw.get("lat"),
            "lng": raw.get("lng"),
            "flightMode": raw.get("flight_mode"),
            "linkStatus": raw.get("link_status") or "ONLINE",
            "rssi": raw.get("rssi_dbm"),
            "pitch": raw.get("pitch_deg"),
            "roll": raw.get("roll_deg"),
            "yaw": raw.get("yaw_deg"),
            "climbRate": raw.get("climb_rate_mps"),
            "systemStatus": "WARNING" if batt is not None and batt < 20 else (raw.get("system_status") or "UNKNOWN")
        }

    @staticmethod
    def to_governor_context(raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formats telemetry payload consumed by S.I.G.H.T. Core Governor rules.
        """
        return {
            "uav_id": "SIGHT-UAV-01",
            "lat": raw.get("lat", 0.0),
            "lng": raw.get("lng", 0.0),
            "altitude_m": raw.get("altitude_m", 0.0),
            "battery_percent": raw.get("battery_percent", 100.0),
            "is_armed": raw.get("is_armed", False),
            "flight_mode": raw.get("flight_mode", "DISARMED"),
            "timestamp_utc": raw.get("timestamp_utc", "")
        }
