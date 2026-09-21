"""
PROJECT S.I.G.H.T. — Telemetry Manager
Orchestrates high-frequency async telemetry ingestion, conditioning, and dispatch.
"""

import time
import asyncio
import logging
from typing import Dict, Any, Optional, Set, Callable
from .telemetry_models import SimulatorTelemetry
from ..adapters.base_adapter import BaseSimulatorAdapter

logger = logging.getLogger("SIGHT.TelemetryManager")


class TelemetryManager:
    """
    Central telemetry management service.
    Polls active simulator adapter at configured rate (5-20 Hz)
    and broadcasts to WebSocket clients and backend storage.
    """

    def __init__(self, adapter: BaseSimulatorAdapter, rate_hz: float = 10.0):
        self.adapter = adapter
        self.rate_hz = max(1.0, min(30.0, rate_hz))
        self._interval = 1.0 / self.rate_hz
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._listeners: Set[Callable[[Dict[str, Any]], asyncio.Future]] = set()
        self._latest_telemetry: Dict[str, Any] = {}
        self._last_update_time = 0.0

    @property
    def latest_telemetry(self) -> Dict[str, Any]:
        return self._latest_telemetry

    def add_listener(self, listener: Callable[[Dict[str, Any]], Any]):
        """Registers a callback or async queue for new telemetry frames."""
        self._listeners.add(listener)

    def remove_listener(self, listener: Callable[[Dict[str, Any]], Any]):
        """Unregisters a telemetry listener."""
        self._listeners.discard(listener)

    def set_adapter(self, adapter: BaseSimulatorAdapter):
        """Switches the active simulator adapter."""
        self.adapter = adapter
        logger.info(f"[SIM] TelemetryManager adapter switched to {adapter.mode_name}")

    async def start(self):
        """Starts the background telemetry polling loop."""
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._poll_loop())
        logger.info(f"[SIM] TelemetryManager started at {self.rate_hz} Hz.")

    async def stop(self):
        """Stops the telemetry polling loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        logger.info("[SIM] TelemetryManager stopped.")

    async def _poll_loop(self):
        while self._running:
            start_t = time.time()
            try:
                if not self.adapter.is_connected:
                    await asyncio.sleep(self._interval)
                    continue
                telem = await self.adapter.get_telemetry()
                self._latest_telemetry = telem
                self._last_update_time = start_t

                # Broadcast to all registered subscribers
                for listener in list(self._listeners):
                    try:
                        res = listener(telem)
                        if asyncio.iscoroutine(res):
                            await res
                    except Exception as e:
                        logger.debug(f"[SIM] Error in telemetry listener: {e}")

            except Exception as e:
                logger.error(f"[SIM] Error polling telemetry from adapter: {e}")

            elapsed = time.time() - start_t
            sleep_time = max(0.005, self._interval - elapsed)
            await asyncio.sleep(sleep_time)
