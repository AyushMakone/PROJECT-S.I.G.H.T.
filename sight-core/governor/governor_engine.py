"""
PROJECT S.I.G.H.T. Core - Autonomous Governor Decision Engine
Implements deterministic, explainable rule hierarchy:
1. comm unavailable -> RETAIN
2. battery <= RTH   -> RETAIN
3. not relevant     -> SUPPRESS
4. confidence low   -> RETAIN
5. outside zone     -> RETAIN
6. persistence low  -> RETAIN
7. evidence req     -> EVIDENCE
8. otherwise        -> EVENT
"""

import time
from typing import Dict, Any, Optional
from ..models.detection import PerceptionDetection
from ..models.decision import GovernorDecision, GovernorState, EvaluatedConditions
from ..context.context_engine import ContextEngine

class GovernorEngine:
    """
    Evaluates perception detections in operational context to produce communication decisions.
    """
    def __init__(self, context_engine: ContextEngine):
        self.context_engine = context_engine

    def evaluate(
        self,
        detection: PerceptionDetection,
        uav_battery_percent: float,
        communication_available: bool = True
    ) -> GovernorDecision:
        """
        Executes the deterministic 8-step S.I.G.H.T. Governor rule evaluation.
        """
        evaluated_conditions, extra = self.context_engine.evaluate_context(
            detection=detection,
            uav_battery_percent=uav_battery_percent,
            communication_available=communication_available
        )

        mission_id = self.context_engine.mission_manager.active_card.mission_id
        timestamp_now = time.strftime("%H:%M:%S UTC", time.gmtime())
        target_class = detection.object_class
        target_id = detection.id
        zone_name = extra.get("zone_name")

        # --- Rule 1: Communication unavailable -> RETAIN ---
        if not evaluated_conditions.communication_available:
            return GovernorDecision(
                decision="RETAIN",
                reason="Mission-data communication channel unavailable. Detection metadata cached in edge NVMe buffer.",
                action="Buffer detection locally. Inhibit RF transmitter.",
                evaluatedConditions=evaluated_conditions,
                timestamp=timestamp_now,
                missionId=mission_id,
                targetId=target_id,
                targetType=target_class,
                zoneName=zone_name
            )

        # --- Rule 2: Battery at/below RTH threshold -> RETAIN ---
        if not evaluated_conditions.battery_above_threshold:
            rth_pct = extra.get("rth_threshold", 20.0)
            cur_pct = extra.get("current_battery", 0.0)
            return GovernorDecision(
                decision="RETAIN",
                reason=f"UAV battery level ({cur_pct:.1f}%) is at or below emergency RTH safety threshold ({rth_pct:.1f}%). RF bursts halted to conserve recovery flight power.",
                action="Cease non-critical RF emissions. Retain detections locally.",
                evaluatedConditions=evaluated_conditions,
                timestamp=timestamp_now,
                missionId=mission_id,
                targetId=target_id,
                targetType=target_class,
                zoneName=zone_name
            )

        # --- Rule 3: Object not mission relevant -> SUPPRESS ---
        if not evaluated_conditions.relevant_object:
            return GovernorDecision(
                decision="SUPPRESS",
                reason=f"Detected object '{target_class}' is outside mission relevance scope.",
                action="Discard detection at edge perception layer. Zero RF emissions radiated.",
                evaluatedConditions=evaluated_conditions,
                timestamp=timestamp_now,
                missionId=mission_id,
                targetId=target_id,
                targetType=target_class,
                zoneName=zone_name
            )

        # --- Rule 4: Confidence below configured threshold -> RETAIN ---
        if not evaluated_conditions.confidence_satisfied:
            min_c = extra.get("min_confidence", 60.0)
            return GovernorDecision(
                decision="RETAIN",
                reason=f"Detection confidence ({detection.confidence:.1f}%) is below operational reliability threshold ({min_c:.1f}%).",
                action="Cache candidate detection in edge buffer. Await frame verification before RF emission.",
                evaluatedConditions=evaluated_conditions,
                timestamp=timestamp_now,
                missionId=mission_id,
                targetId=target_id,
                targetType=target_class,
                zoneName=zone_name
            )

        # --- Rule 5: Outside mission/priority zone -> RETAIN ---
        if not evaluated_conditions.inside_priority_zone:
            return GovernorDecision(
                decision="RETAIN",
                reason=f"Mission-relevant {target_class} detected outside designated priority surveillance zones.",
                action="Retain detection in edge NVMe circular buffer without RF radiation.",
                evaluatedConditions=evaluated_conditions,
                timestamp=timestamp_now,
                missionId=mission_id,
                targetId=target_id,
                targetType=target_class,
                zoneName="Outside Priority Zone"
            )

        # --- Rule 6: Persistence not satisfied -> RETAIN ---
        if not evaluated_conditions.persistence_satisfied:
            req_p = extra.get("required_persistence", 2)
            return GovernorDecision(
                decision="RETAIN",
                reason=f"Relevant {target_class} detected inside priority zone but persistence count ({detection.persistence} frames) has not met threshold ({req_p} frames).",
                action="Update track persistence counter in edge RAM. Suppress RF transmission pending verification.",
                evaluatedConditions=evaluated_conditions,
                timestamp=timestamp_now,
                missionId=mission_id,
                targetId=target_id,
                targetType=target_class,
                zoneName=zone_name
            )

        # --- Rule 7: Evidence required -> EVIDENCE ---
        if evaluated_conditions.evidence_required:
            return GovernorDecision(
                decision="EVIDENCE",
                reason=f"Mission-relevant {target_class} confirmed inside priority zone with required persistence; Mission Card requires visual evidence capture.",
                action="Package high-resolution snapshot and transmit evidence packet according to communication policy.",
                evaluatedConditions=evaluated_conditions,
                timestamp=timestamp_now,
                missionId=mission_id,
                targetId=target_id,
                targetType=target_class,
                zoneName=zone_name
            )

        # --- Rule 8: Otherwise -> EVENT ---
        return GovernorDecision(
            decision="EVENT",
            reason=f"Mission-relevant {target_class} verified inside {zone_name or 'priority zone'} with required persistence threshold satisfied.",
            action="Transmit compact event metadata packet over tactical data link.",
            evaluatedConditions=evaluated_conditions,
            timestamp=timestamp_now,
            missionId=mission_id,
            targetId=target_id,
            targetType=target_class,
            zoneName=zone_name
        )
