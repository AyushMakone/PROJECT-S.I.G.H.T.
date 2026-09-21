from dataclasses import dataclass
from typing import Optional

from simulator.adapters.px4_adapter import PX4Adapter


@dataclass
class MavlinkConnection:
    endpoint: str = "udp:127.0.0.1:14550"
    adapter: Optional[PX4Adapter] = None

    @property
    def connection_string(self) -> str:
        return self.endpoint

    @property
    def connected(self) -> bool:
        return bool(self.adapter and self.adapter.is_connected)

    async def connect(self) -> bool:
        if self.adapter is None or self.adapter.connection_string != self.endpoint:
            self.adapter = PX4Adapter(connection_string=self.endpoint)
        return await self.adapter.connect()

    async def disconnect(self) -> None:
        if self.adapter:
            await self.adapter.disconnect()


async def create_connection(connection: str) -> MavlinkConnection:
    link = MavlinkConnection(endpoint=connection or "udp:127.0.0.1:14550")
    await link.connect()
    return link
