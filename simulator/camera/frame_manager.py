"""
PROJECT S.I.G.H.T. — Frame Manager
Coordinates optical frame acquisition, resizing, throttling, and JPEG encoding for Edge AI.
"""

import cv2
import time
import asyncio
import logging
import threading
from typing import Optional, Tuple
import numpy as np

from .camera_stream import CameraStream

logger = logging.getLogger("SIGHT.FrameManager")


class FrameManager:
    """
    Manages optical camera frames for Edge AI detection and Command Centre preview.
    Optimized for resource conservation: configurable FPS and resolution.
    """

    def __init__(
        self,
        target_width: int = 640,
        target_height: int = 480,
        max_fps: int = 15,
        stream_url: Optional[str] = None
    ):
        self.target_width = target_width
        self.target_height = target_height
        self.max_fps = max(1, min(30, max_fps))
        self._min_frame_interval = 1.0 / self.max_fps

        self.stream = CameraStream(stream_url or "")
        self._latest_frame: Optional[np.ndarray] = None
        self._latest_jpeg: Optional[bytes] = None
        self._last_capture_time = 0.0
        self._lock = threading.Lock()
        self._running = False
        self._frame_count = 0

    @property
    def is_active(self) -> bool:
        return (time.time() - self._last_capture_time) < 3.0

    @property
    def frame_count(self) -> int:
        return self._frame_count

    def update_frame(self, frame: np.ndarray) -> None:
        """
        Ingests a new raw frame from simulator adapter or camera stream,
        resizes to target dimensions, and caches encoded JPEG.
        """
        now = time.time()
        if (now - self._last_capture_time) < self._min_frame_interval:
            return # Rate limit to save CPU/GPU cycles

        if frame is None:
            return

        # Resize if dimensions differ
        h, w = frame.shape[:2]
        if w != self.target_width or h != self.target_height:
            resized = cv2.resize(frame, (self.target_width, self.target_height), interpolation=cv2.INTER_AREA)
        else:
            resized = frame

        # JPEG encode for web streaming
        ret, jpeg = cv2.imencode(".jpg", resized, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
        jpeg_bytes = jpeg.tobytes() if ret else None

        with self._lock:
            self._latest_frame = resized
            self._latest_jpeg = jpeg_bytes
            self._last_capture_time = now
            self._frame_count += 1

    async def get_latest_frame(self) -> Optional[np.ndarray]:
        """Returns the latest frame as a numpy array for Edge AI detector."""
        with self._lock:
            if self._latest_frame is not None:
                return self._latest_frame.copy()
        # Check stream
        stream_frame = self.stream.get_latest_frame()
        if stream_frame is not None:
            self.update_frame(stream_frame)
            return stream_frame
        return None

    def get_latest_jpeg(self) -> Optional[bytes]:
        """Returns the latest frame encoded as JPEG bytes."""
        with self._lock:
            return self._latest_jpeg

    def start_stream(self, stream_url: str):
        self.stream.start(stream_url)

    def stop(self):
        self.stream.stop()
