from typing import Any, Dict, Optional

from .connection import MavlinkConnection


class MavlinkClient:
    """Thin compatibility wrapper around the real pymavlink simulator adapter."""

    def __init__(self, connection: Optional[MavlinkConnection] = None):
        self.connection = connection or MavlinkConnection()

    @property
    def adapter(self):
        return self.connection.adapter

    async def connect(self, connection: Optional[str] = None) -> Dict[str, Any]:
        if connection:
            self.connection = MavlinkConnection(endpoint=connection)
        connected = await self.connection.connect()
        adapter = self.connection.adapter
        return {
            "connected": connected,
            "connection": self.connection.connection_string,
            "system_id": getattr(adapter, "target_system", None),
            "component_id": getattr(adapter, "target_component", None),
        }

    async def disconnect(self) -> None:
        await self.connection.disconnect()

    async def arm(self) -> Dict[str, Any]:
        return await self._command("arm", "armed")

    async def disarm(self) -> Dict[str, Any]:
        return await self._command("disarm", "disarmed")

    async def takeoff(self, altitude: float = 10.0) -> Dict[str, Any]:
        return await self._command("takeoff", "takeoff", altitude)

    async def land(self) -> Dict[str, Any]:
        return await self._command("land", "land")

    async def rtl(self) -> Dict[str, Any]:
        return await self._command("return_to_home", "rtl")

    async def emergency_stop(self) -> Dict[str, Any]:
        return await self._command("disarm", "emergency_stop")

    async def _command(self, method: str, actual_state: str, *args: Any) -> Dict[str, Any]:
        adapter = self.adapter
        if not adapter or not adapter.is_connected:
            return {"requested": False, "accepted": False, "rejected": True, "timeout": False, "actual_state": "unknown"}
        accepted = await getattr(adapter, method)(*args)
        return {"requested": True, "accepted": accepted, "rejected": not accepted, "timeout": False, "actual_state": actual_state if accepted else "unknown"}
