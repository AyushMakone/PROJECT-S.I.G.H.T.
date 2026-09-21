from typing import Any, Dict


def _coerce_optional_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_telemetry(raw: Dict[str, Any] | None = None) -> Dict[str, Any]:
    payload = raw or {}
    return {
        "runtime": "ardupilot_sitl",
        "connected": bool(payload.get("connected", True)),
        "system_id": payload.get("system_id", 1),
        "component_id": payload.get("component_id", 1),
        "autopilot": payload.get("autopilot", "ArduPilot"),
        "vehicle": payload.get("vehicle", "ArduCopter"),
        "armed": bool(payload.get("armed", False)),
        "mode": payload.get("mode", "STABILIZE"),
        "latitude": _coerce_optional_float(payload.get("latitude")),
        "longitude": _coerce_optional_float(payload.get("longitude")),
        "altitude": _coerce_optional_float(payload.get("altitude")),
        "ground_speed": _coerce_optional_float(payload.get("ground_speed")),
        "heading": _coerce_optional_float(payload.get("heading")),
        "battery": _coerce_optional_float(payload.get("battery")),
    }
