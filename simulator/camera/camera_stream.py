"""
PROJECT S.I.G.H.T. — Camera Stream Transport
Connects to external camera stream sources (RTSP, HTTP, MJPEG, or local video feed).
"""

import cv2
import time
import logging
import threading
from typing import Optional
import numpy as np

logger = logging.getLogger("SIGHT.CameraStream")


class CameraStream:
    """
    Asynchronous frame capture from an external camera stream URL.
    """

    def __init__(self, stream_url: str = ""):
        self.stream_url = stream_url
        self._cap: Optional[cv2.VideoCapture] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._latest_frame: Optional[np.ndarray] = None
        self._lock = threading.Lock()
        self._last_frame_time = 0.0

    @property
    def is_active(self) -> bool:
        return self._running and (time.time() - self._last_frame_time) < 3.0

    def start(self, url: Optional[str] = None):
        if url:
            self.stream_url = url
        if not self.stream_url:
            return

        self._running = True
        self._thread = threading.Thread(target=self._capture_worker, daemon=True, name="CameraStream-Rx")
        self._thread.start()
        logger.info(f"[SIM] Camera stream capture started for {self.stream_url}")

    def stop(self):
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        if self._cap:
            self._cap.release()
            self._cap = None
        logger.info("[SIM] Camera stream stopped.")

    def get_latest_frame(self) -> Optional[np.ndarray]:
        with self._lock:
            return self._latest_frame.copy() if self._latest_frame is not None else None

    def _capture_worker(self):
        self._cap = cv2.VideoCapture(self.stream_url)
        while self._running and self._cap and self._cap.isOpened():
            ret, frame = self._cap.read()
            if not ret or frame is None:
                time.sleep(0.05)
                continue
            with self._lock:
                self._latest_frame = frame
                self._last_frame_time = time.time()
