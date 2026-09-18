"""
PROJECT S.I.G.H.T. Core - Governor Decision Output Model
Standardized schema for all decisions produced by the S.I.G.H.T. Governor.
"""

from typing import Literal, Optional, Dict, Any
from pydantic import BaseModel, Field

GovernorState = Literal["SUPPRESS", "RETAIN", "EVENT", "EVIDENCE"]

class EvaluatedConditions(BaseModel):
    communication_available: bool = Field(..., alias="communicationAvailable")
    battery_above_threshold: bool = Field(..., alias="batteryAboveThreshold")
    relevant_object: bool = Field(..., alias="relevantObject")
    confidence_satisfied: bool = Field(..., alias="confidenceSatisfied")
    inside_priority_zone: bool = Field(..., alias="insidePriorityZone")
    persistence_satisfied: bool = Field(..., alias="persistenceSatisfied")
    evidence_required: bool = Field(..., alias="evidenceRequired")

    model_config = {
        "populate_by_name": True
    }

class GovernorDecision(BaseModel):
    decision: GovernorState
    reason: str
    action: str
    evaluated_conditions: EvaluatedConditions = Field(..., alias="evaluatedConditions")
    timestamp: str
    mission_id: str = Field(..., alias="missionId")
    target_id: Optional[str] = Field(default=None, alias="targetId")
    target_type: Optional[str] = Field(default=None, alias="targetType")
    zone_name: Optional[str] = Field(default=None, alias="zoneName")

    model_config = {
        "populate_by_name": True
    }
