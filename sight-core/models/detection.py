"""
PROJECT S.I.G.H.T. Core - Perception Detection Model
Schema for detections emitted by the Edge AI perception stack.
"""

from typing import Tuple, Optional
from pydantic import BaseModel, Field

class PerceptionDetection(BaseModel):
    id: str
    object_class: str = Field(..., alias="objectClass")
    confidence: float
    norm_bbox: Tuple[float, float, float, float] = Field(..., alias="normBbox") # (x, y, w, h)
    track_id: int = Field(default=1, alias="trackId")
    persistence: int = 1
    lat: float
    lng: float
    altitude_m: float = Field(default=0.0, alias="altitudeM")
    timestamp: str
    frame_id: Optional[int] = Field(default=0, alias="frameId")

    model_config = {
        "populate_by_name": True
    }
