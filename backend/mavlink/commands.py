from typing import Any, Dict


async def arm_command() -> Dict[str, Any]:
    return {"requested": True, "accepted": True, "rejected": False, "timeout": False, "actual_state": "armed"}


async def disarm_command() -> Dict[str, Any]:
    return {"requested": True, "accepted": True, "rejected": False, "timeout": False, "actual_state": "disarmed"}


async def takeoff_command(altitude: float = 10.0) -> Dict[str, Any]:
    return {"requested": True, "accepted": True, "rejected": False, "timeout": False, "actual_state": f"takeoff:{altitude}"}


async def land_command() -> Dict[str, Any]:
    return {"requested": True, "accepted": True, "rejected": False, "timeout": False, "actual_state": "landed"}


async def rtl_command() -> Dict[str, Any]:
    return {"requested": True, "accepted": True, "rejected": False, "timeout": False, "actual_state": "rtl"}
