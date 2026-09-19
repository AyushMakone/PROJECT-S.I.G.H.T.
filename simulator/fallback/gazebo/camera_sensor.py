"""
PROJECT S.I.G.H.T. - Simulated UAV Camera Sensor
Generates real optical frames with configurable resolution, frame rate,
timestamp overlay, and optical view of synthetic targets (Person, Vehicle, Animal).
"""

import cv2
import numpy as np
import time
from typing import Tuple, List, Dict, Any, Optional
from .world_server import GazeboWorldServer

class UAVCameraSensor:
    """
    Simulated gimbal-mounted camera producing real image frames for Edge AI pipeline.
    """
    def __init__(
        self,
        world: GazeboWorldServer,
        width: int = 640,
        height: int = 480,
        fps: int = 15,
        hfov_deg: float = 75.0,
        vfov_deg: float = 55.0
    ):
        self.world = world
        self.width = width
        self.height = height
        self.fps = fps
        self.hfov_deg = hfov_deg
        self.vfov_deg = vfov_deg

        self.last_frame: Optional[np.ndarray] = None
        self.last_frame_time: float = 0.0
        self.frame_count: int = 0

    def capture_frame(
        self,
        uav_lat: float,
        uav_lng: float,
        uav_alt_m: float,
        uav_heading_deg: float,
        target_timestamp: Optional[str] = None
    ) -> np.ndarray:
        """
        Synthesizes a real optical camera frame based on current UAV pose and world objects.
        """
        self.frame_count += 1
        now_ts = target_timestamp or time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())

        # 1. Base terrain background (procedural aerial texture with desert/proving ground palette)
        # Create subtle terrain hue based on coordinates
        base_color = np.array([55, 75, 65], dtype=np.uint8) # Dark olive/tactical ground
        frame = np.full((self.height, self.width, 3), base_color, dtype=np.uint8)

        # Draw road / perimeter track across the frame
        road_y = int(self.height * 0.55)
        cv2.line(frame, (0, road_y), (self.width, road_y + 20), (75, 80, 85), 32)
        cv2.line(frame, (0, road_y), (self.width, road_y + 20), (130, 135, 140), 2)

        # Draw perimeter fence wire line
        fence_y = int(self.height * 0.35)
        cv2.line(frame, (0, fence_y), (self.width, fence_y - 15), (45, 50, 55), 3)

        # Add subtle sensor noise for realism
        noise = np.random.normal(0, 4, frame.shape).astype(np.int16)
        frame = np.clip(frame.astype(np.int16) + noise, 0, 255).astype(np.uint8)

        # 2. Query visible entities from the Gazebo world server
        targets = self.world.get_entities_in_camera_fov(
            uav_lat, uav_lng, uav_alt_m, uav_heading_deg, self.hfov_deg, self.vfov_deg
        )

        for target in targets:
            norm_x, norm_y, norm_w, norm_h = target["norm_bbox"]
            px = int(norm_x * self.width)
            py = int(norm_y * self.height)
            pw = max(16, int(norm_w * self.width))
            ph = max(16, int(norm_h * self.height))

            # Center bounding box
            x1 = max(0, px - pw // 2)
            y1 = max(0, py - ph // 2)
            x2 = min(self.width - 1, px + pw // 2)
            y2 = min(self.height - 1, py + ph // 2)

            # Draw target representation based on object class
            obj_class = target["class"]
            if obj_class == "Vehicle":
                # Vehicle body: rectangular dark chassis with windshield
                cv2.rectangle(frame, (x1, y1), (x2, y2), (25, 25, 30), -1)
                cv2.rectangle(frame, (x1 + 2, y1 + 2), (x2 - 2, y2 - 2), (40, 60, 80), -1)
                # Windshield reflection
                cv2.rectangle(frame, (x1 + 4, y1 + 4), (x2 - 4, y1 + 8), (120, 160, 200), -1)
            elif obj_class == "Person":
                # Person body: upright silhouette with head circle
                head_r = max(2, (x2 - x1) // 3)
                head_center = (px, y1 + head_r)
                cv2.circle(frame, head_center, head_r, (40, 45, 50), -1)
                cv2.rectangle(frame, (x1 + 1, y1 + head_r * 2), (x2 - 1, y2), (30, 35, 40), -1)
            elif obj_class == "Animal":
                # Animal body: horizontal silhouette with low profile
                cv2.ellipse(frame, (px, py), (pw // 2, ph // 3), 0, 0, 360, (50, 40, 30), -1)

        # 3. Add tactical HUD overlay and telemetry header
        # Top banner
        cv2.rectangle(frame, (0, 0), (self.width, 24), (10, 15, 20), -1)
        hud_text = f"SIGHT-UAV-01 | LAT: {uav_lat:.5f} LNG: {uav_lng:.5f} | ALT: {uav_alt_m:.1f}m HDG: {int(uav_heading_deg)}deg"
        cv2.putText(frame, hud_text, (8, 16), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 230, 255), 1, cv2.LINE_AA)

        # Bottom banner with timestamp and resolution
        cv2.rectangle(frame, (0, self.height - 20), (self.width, self.height), (10, 15, 20), -1)
        bottom_text = f"{now_ts} | RES: {self.width}x{self.height} @ {self.fps}FPS | FRAME: #{self.frame_count:05d}"
        cv2.putText(frame, bottom_text, (8, self.height - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (160, 175, 190), 1, cv2.LINE_AA)

        # Crosshairs in center
        cx, cy = self.width // 2, self.height // 2
        cv2.line(frame, (cx - 10, cy), (cx + 10, cy), (0, 230, 255), 1)
        cv2.line(frame, (cx, cy - 10), (cx, cy + 10), (0, 230, 255), 1)

        self.last_frame = frame
        self.last_frame_time = time.time()
        return frame

    def get_latest_frame_jpeg(self, quality: int = 85) -> Optional[bytes]:
        """Encodes latest frame to JPEG bytes."""
        if self.last_frame is None:
            return None
        success, encoded = cv2.imencode(".jpg", self.last_frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
        if success:
            return encoded.tobytes()
        return None

    def save_snapshot(self, filepath: str) -> bool:
        """Saves current camera frame to disk."""
        if self.last_frame is None:
            return False
        return cv2.imwrite(filepath, self.last_frame)
