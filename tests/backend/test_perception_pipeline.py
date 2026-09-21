import asyncio
import os
import sys

import numpy as np

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from backend import detector as detector_module
from backend import main as backend_main
from backend.schemas import DetectionRequest, TelemetryData


class FakeWorld:
    def __init__(self, targets):
        self.targets = targets

    def get_entities_in_camera_fov(self, **kwargs):
        return list(self.targets)


class FakeCameraProvider:
    def __init__(self, targets):
        self.world = FakeWorld(targets)


class FakeAdapter:
    def __init__(self, targets):
        self._camera_provider = FakeCameraProvider(targets)

    async def get_camera_frame(self):
        return np.zeros((8, 8, 3), dtype=np.uint8)


def test_world_target_normalization_preserves_identity_and_position():
    target = {
        "entity_id": "VEH-01",
        "class": "Vehicle",
        "lat": 34.0621,
        "lng": -117.8038,
        "norm_bbox": (0.4, 0.5, 0.1, 0.2),
    }

    normalized = detector_module.normalize_world_target(target)

    assert normalized["id"] == "VEH-01"
    assert normalized["entity_type"] == "Vehicle"
    assert normalized["lat"] == target["lat"]
    assert normalized["lng"] == target["lng"]
    assert normalized["persistence"] == 1


def test_virtual_detector_output_builds_detection_request():
    detector = detector_module.VirtualDetector(confidence_noise_std=0.0)
    target = detector_module.normalize_world_target({
        "entity_id": "VEH-01",
        "class": "Vehicle",
        "lat": 28.71,
        "lng": 77.115,
        "norm_bbox": (0.4, 0.5, 0.1, 0.2),
    })

    detections = detector.detect(
        frame=np.zeros((8, 8, 3), dtype=np.uint8),
        uav_lat=28.71,
        uav_lng=77.115,
        altitude_m=80.0,
        timestamp="12:00:00 UTC",
        visible_targets=[target],
    )

    assert len(detections) == 1
    request = DetectionRequest.model_validate(detections[0])
    assert request.object_class == "Vehicle"
    assert request.track_id == 1
    assert request.persistence == 1
    assert request.frame_id == 0
    assert request.lat == 28.71
    assert request.lng == 77.115
    assert request.norm_bbox == (0.4, 0.5, 0.1, 0.2)
    assert request.source == "VIRTUAL_DETECTOR"


def test_virtual_detector_keeps_stable_track_id_and_unique_detection_ids():
    detector = detector_module.VirtualDetector(confidence_noise_std=0.0)
    target = detector_module.normalize_world_target({
        "entity_id": "VEH-01",
        "class": "Vehicle",
        "lat": 28.71,
        "lng": 77.115,
        "norm_bbox": (0.4, 0.5, 0.1, 0.2),
    })

    first = detector.detect(np.zeros((2, 2, 3), dtype=np.uint8), 28.71, 77.115, 80.0, "t1", [target])[0]
    second = detector.detect(np.zeros((2, 2, 3), dtype=np.uint8), 28.71, 77.115, 80.0, "t2", [target])[0]

    assert first["trackId"] == second["trackId"]
    assert first["id"] != second["id"]
    assert first["persistence"] == second["persistence"] == 1


def test_yolo_class_mapping_uses_correct_coco_boat_and_traffic_light_ids():
    assert detector_module.DetectionNormalizer.sight_class(8) == "Vessel"
    assert detector_module.DetectionNormalizer.sight_class(9) is None
    assert detector_module.DetectionNormalizer.sight_class(1) == "Vehicle"


def test_stable_tracker_increments_persistence_and_resets_after_expiration():
    tracker = detector_module.StableTracker(iou_threshold=0.3, max_missed_frames=1)
    first = tracker.update([
        {"objectClass": "Person", "normBbox": (0.5, 0.5, 0.2, 0.2)}
    ], frame_id=1, timestamp="t1")[0]
    second = tracker.update([
        {"objectClass": "Person", "normBbox": (0.51, 0.5, 0.2, 0.2)}
    ], frame_id=2, timestamp="t2")[0]
    assert first["trackId"] == second["trackId"]
    assert second["persistence"] == 2

    tracker.update([], frame_id=3, timestamp="t3")
    tracker.update([], frame_id=4, timestamp="t4")
    replacement = tracker.update([
        {"objectClass": "Person", "normBbox": (0.5, 0.5, 0.2, 0.2)}
    ], frame_id=5, timestamp="t5")[0]
    assert replacement["trackId"] != first["trackId"]
    assert replacement["persistence"] == 1


def test_yolo_adapter_consumes_frame_and_converts_model_output():
    class FakeBox:
        cls = np.array([0])
        conf = np.array([0.74])
        xyxyn = np.array([[0.2, 0.3, 0.6, 0.7]])

    class FakeResult:
        boxes = [FakeBox()]

    class FakeModel:
        def __call__(self, frame, **kwargs):
            assert frame.shape == (480, 640, 3)
            assert frame.dtype == np.uint8
            return [FakeResult()]

    detector = detector_module.YOLODetector.__new__(detector_module.YOLODetector)
    detector._model_path = "test-model.pt"
    detector.device = "cpu"
    detector.confidence_threshold = 0.25
    detector._model = FakeModel()
    detector._available = True
    detector.load_error = None
    detector.tracker = detector_module.StableTracker()
    detector.persistence = detector_module.PersistenceManager()
    detector._detection_counter = 0
    detector.last_inference_ms = None
    detector.inference_count = 0
    detector.last_successful_inference = None

    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    detections = detector.detect(frame, 34.0, -117.0, 10.0, "t1", frame_id=1)
    assert detections[0]["objectClass"] == "Person"
    assert detections[0]["confidence"] == 74.0
    assert detections[0]["normBbox"] == (0.4, 0.5, 0.39999999999999997, 0.39999999999999997)
    assert detections[0]["trackId"] == 1
    assert detections[0]["persistence"] == 1
    assert detections[0]["locationSource"] == "UAV_POSITION"
    assert detector.inference_count == 1


def test_internal_processing_routes_detection_to_existing_governor(monkeypatch):
    monkeypatch.setattr(backend_main, "_telemetry_store", TelemetryData(battery_percent=80.0))
    monkeypatch.setattr(backend_main, "_detection_log", [])
    monkeypatch.setattr(backend_main, "_decision_log", [])
    monkeypatch.setattr(backend_main, "_latest_governor_state", None)
    monkeypatch.setattr(backend_main, "_comm_controller", backend_main.CommunicationController(link_available=True))

    request = DetectionRequest.model_validate({
        "id": "DET-VEH-01",
        "objectClass": "Vehicle",
        "confidence": 80.0,
        "normBbox": [0.4, 0.5, 0.1, 0.2],
        "trackId": 1,
        "persistence": 1,
        "lat": 28.71,
        "lng": 77.115,
        "altitudeM": 80.0,
        "timestamp": "12:00:00 UTC",
        "frameId": 0,
        "source": "VIRTUAL_DETECTOR",
    })

    response = backend_main.process_detection_request(request, battery_percent_override=80.0)

    assert response.decision == "RETAIN"
    assert len(backend_main._detection_log) == 1
    assert len(backend_main._decision_log) == 1
    assert len(backend_main._comm_controller.get_retained_buffer()) == 1


def test_perception_cycle_processes_multiple_targets_individually(monkeypatch):
    targets = [
        {"entity_id": "VEH-01", "class": "Vehicle", "lat": 28.71, "lng": 77.115},
        {"entity_id": "ANI-01", "class": "Animal", "lat": 28.71, "lng": 77.115},
    ]
    monkeypatch.setattr(backend_main, "_sim_adapter", FakeAdapter(targets))
    monkeypatch.setattr(backend_main, "_detector", detector_module.VirtualDetector(confidence_noise_std=0.0))
    monkeypatch.setattr(backend_main, "_perception_last_inference", 0.0)
    monkeypatch.setattr(backend_main, "_detection_log", [])
    monkeypatch.setattr(backend_main, "_decision_log", [])
    monkeypatch.setattr(backend_main, "_latest_governor_state", None)
    monkeypatch.setattr(backend_main, "_comm_controller", backend_main.CommunicationController(link_available=True))
    monkeypatch.setattr(backend_main, "_mission_manager", backend_main.MissionCardManager(initial_card=backend_main._mission_manager.active_card))
    monkeypatch.setattr(backend_main, "_context_engine", backend_main.ContextEngine(mission_manager=backend_main._mission_manager))
    monkeypatch.setattr(backend_main, "_governor", backend_main.GovernorEngine(context_engine=backend_main._context_engine))

    asyncio.run(backend_main._on_perception_telemetry_update({
        "lat": 28.71,
        "lng": 77.115,
        "altitude": 80.0,
        "relativeAltitude": 80.0,
        "headingDegrees": 0.0,
        "battery": 80.0,
        "timestamp": "12:00:00 UTC",
    }))

    assert len(backend_main._detection_log) == 2
    assert {entry["objectClass"] for entry in backend_main._detection_log} == {"Vehicle", "Animal"}
    assert len(backend_main._decision_log) == 2


def test_perception_failure_does_not_escape_listener(monkeypatch):
    class FailingDetector:
        backend_name = "VIRTUAL_DETECTOR"

        def detect(self, **kwargs):
            raise RuntimeError("synthetic detector failure")

    monkeypatch.setattr(backend_main, "_sim_adapter", FakeAdapter([]))
    monkeypatch.setattr(backend_main, "_detector", FailingDetector())
    monkeypatch.setattr(backend_main, "_perception_last_inference", 0.0)

    asyncio.run(backend_main._on_perception_telemetry_update({
        "lat": 28.71,
        "lng": 77.115,
        "altitude": 80.0,
        "headingDegrees": 0.0,
        "battery": 80.0,
        "timestamp": "12:00:00 UTC",
    }))


def test_telemetry_manager_listener_set_deduplicates_same_listener():
    from simulator.telemetry.telemetry_manager import TelemetryManager

    manager = TelemetryManager(adapter=None, rate_hz=10.0)
    listener = lambda telemetry: None
    manager.add_listener(listener)
    manager.add_listener(listener)

    assert len(manager._listeners) == 1


def test_perception_listener_registration_is_idempotent_and_cleanup_works(monkeypatch):
    class FakeTelemetryManager:
        def __init__(self):
            self.listeners = set()

        def add_listener(self, listener):
            self.listeners.add(listener)

        def remove_listener(self, listener):
            self.listeners.discard(listener)

    manager = FakeTelemetryManager()
    monkeypatch.setattr(backend_main, "_telemetry_mgr", manager)
    monkeypatch.setattr(backend_main, "_perception_listener_registered", False)

    backend_main._register_perception_listener()
    backend_main._register_perception_listener()
    assert len(manager.listeners) == 1
    assert backend_main._perception_listener_registered is True

    backend_main._unregister_perception_listener()
    assert len(manager.listeners) == 0
    assert backend_main._perception_listener_registered is False


def test_perception_cadence_gate_allows_one_cycle_per_second(monkeypatch):
    class CountingDetector:
        backend_name = "VIRTUAL_DETECTOR"

        def __init__(self):
            self.calls = 0

        def detect(self, **kwargs):
            self.calls += 1
            return []

    detector = CountingDetector()
    monkeypatch.setattr(backend_main, "_detector", detector)
    monkeypatch.setattr(backend_main, "_sim_adapter", FakeAdapter([]))
    monkeypatch.setattr(backend_main, "_perception_last_inference", 0.0)
    monkeypatch.setattr(backend_main, "process_detection_request", lambda request, battery_percent_override=None: None)
    ticks = iter(100.0 + (index * 0.1) for index in range(10))
    monkeypatch.setattr(backend_main, "_perception_clock", lambda: next(ticks))

    telemetry = {
        "lat": 28.71,
        "lng": 77.115,
        "altitude": 80.0,
        "headingDegrees": 0.0,
        "battery": 80.0,
        "timestamp": "12:00:00 UTC",
    }
    for _ in range(10):
        asyncio.run(backend_main._on_perception_telemetry_update(telemetry))

    assert detector.calls == 1
