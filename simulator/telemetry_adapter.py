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
        hdg_idx = int(((raw.get("heading_deg", 0.0) + 22.5) % 360) / 45)
        heading_str = headings[hdg_idx]

        is_armed = raw.get("is_armed", False)
        batt = raw.get("battery_percent", 100.0)

        return {
            "altitude": raw.get("altitude_m", 0.0),
            "speed": raw.get("speed_mps", 0.0),
            "heading": heading_str,
            "headingDegrees": raw.get("heading_deg", 0.0),
            "battery": batt,
            "batteryVoltage": raw.get("battery_voltage_v", 24.6),
            "gpsStatus": "FIXED" if is_armed or raw.get("altitude_m", 0) > 0 else "ACQUIRING",
            "gpsSatellites": 18,
            "hdop": 0.75,
            "lat": raw.get("lat", 34.0522),
            "lng": raw.get("lng", -117.8247),
            "flightMode": raw.get("flight_mode", "DISARMED"),
            "linkStatus": "ONLINE",
            "rssi": -65,
            "pitch": raw.get("pitch_deg", 0.0),
            "roll": raw.get("roll_deg", 0.0),
            "yaw": raw.get("yaw_deg", 0.0),
            "climbRate": raw.get("climb_rate_mps", 0.0),
            "systemStatus": "WARNING" if batt < 20 else "ONLINE"
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
