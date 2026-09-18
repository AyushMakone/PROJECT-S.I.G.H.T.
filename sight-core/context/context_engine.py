"""
PROJECT S.I.G.H.T. Core - Context Engine
Synthesizes Mission Card criteria, UAV avionics (battery, link), and Edge AI target detections
into an evaluated operational context vector.
"""

from typing import Dict, Any, Tuple
from ..models.detection import PerceptionDetection
from ..models.decision import EvaluatedConditions
from ..models.mission_card import MissionCard
from ..mission.mission_card_manager import MissionCardManager
from .geofence import GeofenceClassifier

class ContextEngine:
    """
    Evaluates raw perception metadata against UAV state and Mission Card boundaries.
    """
    def __init__(self, mission_manager: MissionCardManager):
        self.mission_manager = mission_manager

    def evaluate_context(
        self,
        detection: PerceptionDetection,
        uav_battery_percent: float,
        communication_available: bool = True
    ) -> Tuple[EvaluatedConditions, Dict[str, Any]]:
        card = self.mission_manager.active_card
        if not card:
            raise ValueError("No active Mission Card loaded in S.I.G.H.T. Core.")

        # 1. Spatial geofence evaluation
        inside_zone, zone_name = GeofenceClassifier.check_priority_zones(
            detection.lat, detection.lng, card.priority_zones
        )

        # 2. Mission relevance evaluation
        is_relevant = self.mission_manager.is_object_relevant(detection.object_class)

        # 3. Confidence threshold evaluation
        conf_ok = detection.confidence >= card.min_confidence_percent

        # 4. Persistence evaluation
        persistence_ok = self.mission_manager.is_persistence_satisfied(detection.persistence)

        # 5. Battery threshold evaluation
        battery_ok = self.mission_manager.is_battery_safe(uav_battery_percent)

        # 6. Evidence policy evaluation
        evidence_req = self.mission_manager.is_evidence_required()

        evaluated = EvaluatedConditions(
            communicationAvailable=communication_available,
            batteryAboveThreshold=battery_ok,
            relevantObject=is_relevant,
            confidenceSatisfied=conf_ok,
            insidePriorityZone=inside_zone,
            persistenceSatisfied=persistence_ok,
            evidenceRequired=evidence_req
        )

        extra_context = {
            "zone_name": zone_name,
            "min_confidence": card.min_confidence_percent,
            "required_persistence": card.persistence_frames,
            "rth_threshold": card.battery_rth_percent,
            "current_battery": uav_battery_percent
        }

        return evaluated, extra_context
