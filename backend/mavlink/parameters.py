from typing import Any, Dict

PARAMETERS = {
    "ARMING_CHECK": 0,
    "RTL_ALT": 15.0,
    "RTL_BATT_MIN": 20.0,
    "FENCE_ENABLE": 0,
    "WPNAV_SPEED": 10.0,
    "SCR_ENABLE": 0,
    "SIM_WIND_SPD": 0.0,
    "SIM_WIND_DIR": 0.0,
    "SIM_GPS_DISABLE": 0,
}


def get_parameter(name: str) -> Dict[str, Any]:
    value = PARAMETERS.get(name, 0)
    return {"name": name, "value": value}


def set_parameter(name: str, value: Any) -> Dict[str, Any]:
    PARAMETERS[name] = value
    return {"name": name, "value": value}


def list_parameters() -> Dict[str, Any]:
    return {"parameters": PARAMETERS}
