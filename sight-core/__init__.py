"""PROJECT S.I.G.H.T. Core Intelligence & Governance Engine"""
try:
    from .models.mission_card import MissionCard, PriorityZone
    from .models.detection import PerceptionDetection
    from .models.decision import GovernorDecision, EvaluatedConditions
    from .mission.mission_card_manager import MissionCardManager
    from .context.context_engine import ContextEngine
    from .context.geofence import GeofenceClassifier
    from .governor.governor_engine import GovernorEngine
except ImportError:
    # Pytest can load the hyphenated source directory as a standalone path.
    from sight_core.models.mission_card import MissionCard, PriorityZone
    from sight_core.models.detection import PerceptionDetection
    from sight_core.models.decision import GovernorDecision, EvaluatedConditions
    from sight_core.mission.mission_card_manager import MissionCardManager
    from sight_core.context.context_engine import ContextEngine
    from sight_core.context.geofence import GeofenceClassifier
    from sight_core.governor.governor_engine import GovernorEngine

__all__ = [
    "MissionCard",
    "PriorityZone",
    "PerceptionDetection",
    "GovernorDecision",
    "EvaluatedConditions",
    "MissionCardManager",
    "ContextEngine",
    "GeofenceClassifier",
    "GovernorEngine"
]
