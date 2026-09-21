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


def test_world_entities_are_loaded_as_dictionary():
    from simulator.gazebo.world_server import GazeboWorldServer

    world = GazeboWorldServer()
    assert isinstance(world.entities, dict)
    assert "VEH-01" in world.entities
    assert world.entities["VEH-01"].object_class == "Vehicle"


def test_camera_frame_changes_when_pose_changes():
    from simulator.camera.synthetic_camera_provider import SyntheticCameraProvider

    class DummyTelemetry:
        latitude = 34.0522
        longitude = -117.8247
        relative_altitude_m = 40.0
        heading_deg = 0.0

    provider = SyntheticCameraProvider(adapter=DummyTelemetry())
    frame_a = provider.sensor.capture_frame(
        uav_lat=34.0522,
        uav_lng=-117.8247,
        uav_alt_m=40.0,
        uav_heading_deg=0.0,
        target_timestamp="t0",
    )
    frame_b = provider.sensor.capture_frame(
        uav_lat=34.0522,
        uav_lng=-117.8247,
        uav_alt_m=80.0,
        uav_heading_deg=90.0,
        target_timestamp="t1",
    )

    assert frame_a.shape == (480, 640, 3)
    assert frame_b.shape == (480, 640, 3)
    assert not np.array_equal(frame_a, frame_b)


def test_camera_status_tracks_active_synthetic_provider():
    import backend.main as backend_main
    from types import SimpleNamespace

    class DummyAdapter:
        def __init__(self):
            self.is_connected = True
            self.mode_name = "local"
            self.telemetry = SimpleNamespace(
                latitude=34.0522,
                longitude=-117.8247,
                relative_altitude_m=45.0,
                heading_deg=45.0,
            )
            self._camera_provider = None

    backend_main._sim_adapter = DummyAdapter()
    backend_main._sim_adapter._camera_provider = backend_main.SyntheticCameraProvider(adapter=backend_main._sim_adapter)

    backend_main._refresh_camera_state_from_adapter()
    response = backend_main.camera_status()

    assert response["status"] == "CONNECTED"
    assert response["online"] is True
    assert response["fps"] == 15
    assert response["resolution"] == "640x480"
