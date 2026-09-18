"""
PROJECT S.I.G.H.T. Core - Decision Explainability Module
Generates human-readable operator audit explanations and structured decision matrices.
"""

from typing import Dict, Any
from ..models.decision import GovernorDecision

class ExplainabilityFormatter:
    """
    Transforms Governor decisions into operator-facing explainability summaries.
    """
    @staticmethod
    def format_operator_summary(decision: GovernorDecision) -> str:
        """
        Creates a high-level operational explanation for Ground Station displays.
        """
        cond = decision.evaluated_conditions
        summary = (
            f"[{decision.timestamp}] S.I.G.H.T. GOVERNOR → {decision.decision}\n"
            f"Target: {decision.target_type or 'Unknown'} ({decision.target_id or 'N/A'})\n"
            f"Zone:   {decision.zone_name or 'N/A'}\n"
            f"Reason: {decision.reason}\n"
            f"Action: {decision.action}\n"
            f"Conditions Evaluated:\n"
            f"  - Comm Available:        {'YES' if cond.communication_available else 'NO'}\n"
            f"  - Battery > RTH:         {'YES' if cond.battery_above_threshold else 'NO'}\n"
            f"  - Relevant Object:       {'YES' if cond.relevant_object else 'NO'}\n"
            f"  - Confidence Met:        {'YES' if cond.confidence_satisfied else 'NO'}\n"
            f"  - Inside Priority Zone:  {'YES' if cond.inside_priority_zone else 'NO'}\n"
            f"  - Persistence Satisfied: {'YES' if cond.persistence_satisfied else 'NO'}\n"
            f"  - Evidence Required:     {'YES' if cond.evidence_required else 'NO'}"
        )
        return summary

    @staticmethod
    def to_frontend_schema(decision: GovernorDecision) -> Dict[str, Any]:
        """
        Converts to the exact TypeScript GovernorDecision interface used by Command Centre:
        {
          decision: "SUPPRESS" | "RETAIN" | "EVENT" | "EVIDENCE",
          reason: string,
          action: string,
          evaluatedConditions: { ... },
          timestamp: string,
          targetId?: string,
          targetType?: string
        }
        """
        return decision.model_dump(by_alias=True)
