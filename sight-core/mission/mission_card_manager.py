"""
PROJECT S.I.G.H.T. Core - Mission Card Manager
Validates, persists, and queries the UAV-side active Mission Card.
"""

import json
from typing import Dict, Any, Optional
from ..models.mission_card import MissionCard, PriorityZone

class MissionCardManager:
    """
    Manages active Mission Card lifecycle and validation on the UAV companion computer.
    """
    def __init__(self, initial_card: Optional[MissionCard] = None):
        self._active_card: Optional[MissionCard] = initial_card

    @property
    def active_card(self) -> Optional[MissionCard]:
        return self._active_card

    def load_from_dict(self, card_dict: Dict[str, Any]) -> MissionCard:
        card = MissionCard.model_validate(card_dict)
        self._active_card = card
        return card

    def load_from_json_file(self, file_path: str) -> MissionCard:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return self.load_from_dict(data)

    def is_object_relevant(self, object_class: str) -> bool:
        if not self._active_card:
            return False
        # Case-insensitive check
        classes = [c.lower() for c in self._active_card.relevant_objects]
        return object_class.lower() in classes

    def is_persistence_satisfied(self, persistence_count: int) -> bool:
        if not self._active_card:
            return False
        return persistence_count >= self._active_card.persistence_frames

    def is_battery_safe(self, current_battery_percent: float) -> bool:
        if not self._active_card:
            return True
        return current_battery_percent > self._active_card.battery_rth_percent

    def is_evidence_required(self) -> bool:
        if not self._active_card:
            return False
        return self._active_card.evidence == "Enabled"
