"""
PROJECT S.I.G.H.T. Core - Communication & Emission Policies
Handles mission-specific communication constraints such as SILENT, EVENT ONLY,
EVENT & EVIDENCE, and ADAPTIVE link budgeting.
"""

from typing import Dict, Any
from ..models.mission_card import MissionCard, CommunicationPolicyType
from ..models.decision import GovernorState

class CommunicationPolicyHandler:
    """
    Applies mission card communication policy rules to Governor decisions.
    """
    @staticmethod
    def should_transmit_rf(
        decision_state: GovernorState,
        policy: CommunicationPolicyType
    ) -> bool:
        """
        Determines whether the physical radio should radiate RF energy.
        """
        # SILENT policy mandate: zero RF under all circumstances
        if policy == "SILENT":
            return False

        if decision_state == "SUPPRESS":
            return False

        if decision_state == "RETAIN":
            return False

        if decision_state == "EVENT":
            return True

        if decision_state == "EVIDENCE":
            # Transmit only if policy explicitly permits evidence
            return policy in ["EVENT & EVIDENCE", "ADAPTIVE"]

        return False
