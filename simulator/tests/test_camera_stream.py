"""
PROJECT S.I.G.H.T. - Simulated Camera Stream Test
Verifies frame generation, configurable resolution, FPS, and target visibility.
"""

import numpy as np
import pytest
from simulator.simulator_interface import SimulatorInterface

def test_camera_frame_format_and_resolution():
    sim = SimulatorInterface(camera_width=640, camera_height=480, camera_fps=15)
    
    # Capture frame while at cruise altitude over home
    frame = sim.camera.capture_frame(
        uav_lat=34.0522,
        uav_lng=-117.8247,
        uav_alt_m=84.0,
        uav_heading_deg=45.0
    )

    assert isinstance(frame, np.ndarray)
    assert frame.shape == (480, 640, 3)
    assert frame.dtype == np.uint8

    # Verify JPEG encoding produces valid JPEG header (FF D8)
    jpeg_bytes = sim.camera.get_latest_frame_jpeg(quality=80)
    assert jpeg_bytes is not None
    assert len(jpeg_bytes) > 1000
    assert jpeg_bytes[:2] == b'\xff\xd8' # Standard JPEG SOI marker

def test_camera_configurable_high_res():
    sim_hd = SimulatorInterface(camera_width=1280, camera_height=720, camera_fps=20)
    frame_hd = sim_hd.camera.capture_frame(
        uav_lat=34.0522,
        uav_lng=-117.8247,
        uav_alt_m=84.0,
        uav_heading_deg=0.0
    )

    assert frame_hd.shape == (720, 1280, 3)

def test_camera_fov_target_detection():
    sim = SimulatorInterface()
    
    # Position directly above VEH-01 (Priority Zone Alpha: 34.0621, -117.8038) at 84m altitude
    targets = sim.world.get_entities_in_camera_fov(
        uav_lat=34.0621,
        uav_lng=-117.8038,
        uav_alt_m=84.0,
        uav_heading_deg=45.0
    )

    assert len(targets) >= 1
    classes = [t["class"] for t in targets]
    assert "Vehicle" in classes

    # Capture frame with target present and verify no exceptions
    frame = sim.camera.capture_frame(
        uav_lat=34.0621,
        uav_lng=-117.8038,
        uav_alt_m=84.0,
        uav_heading_deg=45.0
    )
    assert frame.shape == (480, 640, 3)
