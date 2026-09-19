"""
PROJECT S.I.G.H.T. — Base Simulator Adapter Interface
Defines standard async contract for all UAV simulator integrations.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
import numpy as np


class BaseSimulatorAdapter(ABC):
    """
    Abstract contract for UAV simulator adapters.
    Connects S.I.G.H.T. to genuine real-time simulation engines.
    """

    @abstractmethod
    async def connect(self) -> bool:
        """Establishes connection to the simulator / MAVLink link."""
        ...

    @abstractmethod
    async def disconnect(self) -> None:
        """Closes connection to the simulator."""
        ...

    @abstractmethod
    async def arm(self) -> bool:
        """Sends genuine ARM command to the simulated autopilot."""
        ...

    @abstractmethod
    async def disarm(self) -> bool:
        """Sends genuine DISARM command to the simulated autopilot."""
        ...

    @abstractmethod
    async def takeoff(self, altitude: float = 10.0) -> bool:
        """Commands simulated vehicle to take off to specified altitude in meters."""
        ...

    @abstractmethod
    async def land(self) -> bool:
        """Commands simulated vehicle to land."""
        ...

    @abstractmethod
    async def hover(self) -> bool:
        """Commands simulated vehicle to hold position / loiter."""
        ...

    @abstractmethod
    async def move(self, vx: float, vy: float, vz: float, yaw_rate: float = 0.0) -> bool:
        """
        Commands velocity in UAV local NED or body frame:
        vx: forward velocity (m/s)
        vy: right velocity (m/s)
        vz: down velocity (m/s, negative is climbing)
        yaw_rate: angular turn rate (deg/s)
        """
        ...

    @abstractmethod
    async def set_heading(self, heading_deg: float) -> bool:
        """Commands vehicle to align with absolute compass heading in degrees."""
        ...

    @abstractmethod
    async def return_to_home(self) -> bool:
        """Commands simulated vehicle to Return To Home / RTL."""
        ...

    @abstractmethod
    async def get_telemetry(self) -> Dict[str, Any]:
        """Returns the latest genuine telemetry dictionary from the simulated vehicle."""
        ...

    @abstractmethod
    async def get_camera_frame(self) -> Optional[np.ndarray]:
        """Returns the latest optical frame from the simulated camera sensor."""
        ...

    @abstractmethod
    async def send_mission(self, mission: Dict[str, Any]) -> bool:
        """Uploads waypoint flight plan to simulated autopilot."""
        ...

    @property
    @abstractmethod
    def mode_name(self) -> str:
        """Returns adapter mode name: 'cloud', 'local', or 'fallback'."""
        ...

    @property
    @abstractmethod
    def is_connected(self) -> bool:
        """Returns True if live connection to simulator is healthy."""
        ...

    @property
    @abstractmethod
    def is_armed(self) -> bool:
        """Returns True if vehicle motors are armed."""
        ...

    @property
    @abstractmethod
    def flight_mode(self) -> str:
        """Returns current autopilot flight mode."""
        ...
