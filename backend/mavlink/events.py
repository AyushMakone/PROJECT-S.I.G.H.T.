from typing import Any, Dict


def build_connection_event(status: str, runtime: str = "ardupilot_sitl") -> Dict[str, Any]:
    return {"type": "connection", "status": status, "runtime": runtime}


def build_telemetry_event(vehicle: Dict[str, Any], timestamp: int = 0) -> Dict[str, Any]:
    return {"type": "telemetry", "timestamp": timestamp, "vehicle": vehicle}


def build_governor_event(state: str, classification: str, confidence: float, reason: str) -> Dict[str, Any]:
    return {"type": "governor", "state": state, "class": classification, "confidence": confidence, "reason": reason}


def build_communication_event(decision: str, transmitted: bool, bytes_count: int = 0) -> Dict[str, Any]:
    return {"type": "communication", "decision": decision, "bytes": bytes_count, "transmitted": transmitted}
