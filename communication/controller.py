"""
PROJECT S.I.G.H.T. — Communication Controller
Phase 5: Mission-data transmission governance layer.

State machine:
  INACTIVE → ACTIVATE → TRANSMIT → VERIFY → INACTIVE

Decision mapping:
  SUPPRESS → no transmission (link stays INACTIVE)
  RETAIN   → local retention (no RF, link stays INACTIVE)
  EVENT    → compact metadata packet (ACTIVATE → TRANSMIT → VERIFY → INACTIVE)
  EVIDENCE → metadata + ROI evidence (ACTIVATE → TRANSMIT → VERIFY → INACTIVE)

NOTE: This controller governs mission-data communication ONLY.
      It does not disable all UAV RF (control link, ADS-B, etc.).
      It does not implement jamming or EW functionality.
"""

import time
import json
import threading
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Literal, List
from enum import Enum


# ─────────────────────────────────────────────
#  State Machine
# ─────────────────────────────────────────────

class CommState(str, Enum):
    INACTIVE = "INACTIVE"
    ACTIVATE = "ACTIVATE"
    TRANSMIT = "TRANSMIT"
    VERIFY   = "VERIFY"


# ─────────────────────────────────────────────
#  Packet Schemas
# ─────────────────────────────────────────────

@dataclass
class EventPacket:
    """Compact metadata packet for EVENT decisions. No image data."""
    packet_id: str
    mission_id: str
    target_type: str
    confidence: float
    lat: float
    lng: float
    altitude_m: float
    zone_name: Optional[str]
    timestamp: str
    governor_decision: str = "EVENT"
    packet_type: str = "EVENT_METADATA"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "packetId": self.packet_id,
            "packetType": self.packet_type,
            "missionId": self.mission_id,
            "governorDecision": self.governor_decision,
            "targetType": self.target_type,
            "confidence": self.confidence,
            "lat": self.lat,
            "lng": self.lng,
            "altitudeM": self.altitude_m,
            "zoneName": self.zone_name,
            "timestamp": self.timestamp,
        }

    def byte_size(self) -> int:
        return len(json.dumps(self.to_dict()).encode("utf-8"))


@dataclass
class EvidencePacket:
    """Extended packet for EVIDENCE decisions. Includes ROI metadata."""
    packet_id: str
    mission_id: str
    target_type: str
    confidence: float
    lat: float
    lng: float
    altitude_m: float
    zone_name: Optional[str]
    timestamp: str
    roi_bbox: tuple           # normalized (x, y, w, h)
    roi_resolution: tuple     # (width, height)
    frame_id: int
    governor_decision: str = "EVIDENCE"
    packet_type: str = "EVIDENCE_METADATA"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "packetId": self.packet_id,
            "packetType": self.packet_type,
            "missionId": self.mission_id,
            "governorDecision": self.governor_decision,
            "targetType": self.target_type,
            "confidence": self.confidence,
            "lat": self.lat,
            "lng": self.lng,
            "altitudeM": self.altitude_m,
            "zoneName": self.zone_name,
            "timestamp": self.timestamp,
            "roiBbox": list(self.roi_bbox),
            "roiResolution": list(self.roi_resolution),
            "frameId": self.frame_id,
        }

    def byte_size(self) -> int:
        return len(json.dumps(self.to_dict()).encode("utf-8"))


# ─────────────────────────────────────────────
#  Retention Buffer
# ─────────────────────────────────────────────

@dataclass
class RetainedDetection:
    """Locally retained detection not transmitted."""
    detection_id: str
    reason: str
    governor_decision: str
    target_type: str
    confidence: float
    lat: float
    lng: float
    timestamp: str
    mission_id: str


# ─────────────────────────────────────────────
#  Statistics
# ─────────────────────────────────────────────

@dataclass
class CommStats:
    packets_sent: int = 0
    bytes_transmitted: int = 0
    events_transmitted: int = 0
    evidence_transmitted: int = 0
    suppressed: int = 0
    retained: int = 0
    total_processed: int = 0
    transmit_durations_ms: List[float] = field(default_factory=list)
    last_transmission_ms: Optional[float] = None

    @property
    def avg_latency_ms(self) -> Optional[float]:
        if not self.transmit_durations_ms:
            return None
        return round(sum(self.transmit_durations_ms) / len(self.transmit_durations_ms), 3)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "packets_sent": self.packets_sent,
            "bytes_transmitted": self.bytes_transmitted,
            "events_transmitted": self.events_transmitted,
            "evidence_transmitted": self.evidence_transmitted,
            "suppressed": self.suppressed,
            "retained": self.retained,
            "total_processed": self.total_processed,
            "avg_latency_ms": self.avg_latency_ms,
            "last_transmission_ms": self.last_transmission_ms,
        }


# ─────────────────────────────────────────────
#  Communication Controller
# ─────────────────────────────────────────────

class CommunicationController:
    """
    S.I.G.H.T. Communication Controller.
    Governs mission-data transmission based on Governor decisions.
    The mission-data channel is INACTIVE by default.
    """

    def __init__(self, link_available: bool = True, simulate_latency_ms: float = 12.0):
        self.link_available = link_available
        self._simulate_latency_ms = simulate_latency_ms  # simulated one-way latency
        self._state = CommState.INACTIVE
        self._stats = CommStats()
        self._retention_buffer: List[RetainedDetection] = []
        self._transmitted_events: List[EventPacket] = []
        self._transmitted_evidence: List[EvidencePacket] = []
        self._lock = threading.Lock()
        self._packet_counter = 0

    @property
    def state(self) -> CommState:
        return self._state

    @property
    def stats(self) -> CommStats:
        return self._stats

    def _next_packet_id(self, prefix: str = "PKT") -> str:
        self._packet_counter += 1
        return f"{prefix}-{self._packet_counter:05d}"

    # ── Main dispatch ──────────────────────────────────────────────────

    def process_decision(
        self,
        governor_decision: str,
        governor_reason: str,
        detection: Dict[str, Any],
        mission_id: str,
    ) -> Dict[str, Any]:
        """
        Routes a Governor decision through the communication state machine.
        Returns transmission result metadata.
        """
        with self._lock:
            self._stats.total_processed += 1
            decision = governor_decision.upper()

            if decision == "SUPPRESS":
                return self._handle_suppress(detection)

            elif decision == "RETAIN":
                return self._handle_retain(detection, governor_reason, mission_id)

            elif decision == "EVENT":
                return self._handle_event(detection, mission_id)

            elif decision == "EVIDENCE":
                return self._handle_evidence(detection, mission_id)

            else:
                return {"status": "ERROR", "reason": f"Unknown decision: {decision}"}

    # ── Decision Handlers ──────────────────────────────────────────────

    def _handle_suppress(self, detection: Dict[str, Any]) -> Dict[str, Any]:
        """SUPPRESS: zero bytes transmitted, link stays INACTIVE."""
        self._stats.suppressed += 1
        self._state = CommState.INACTIVE
        return {
            "status": "SUPPRESSED",
            "bytes_transmitted": 0,
            "state": self._state.value,
            "packet": None,
        }

    def _handle_retain(self, detection: Dict[str, Any], reason: str,
                       mission_id: str) -> Dict[str, Any]:
        """RETAIN: cache locally, no RF emission."""
        self._stats.retained += 1
        self._state = CommState.INACTIVE

        retained = RetainedDetection(
            detection_id=detection.get("id", ""),
            reason=reason,
            governor_decision="RETAIN",
            target_type=detection.get("objectClass", "Unknown"),
            confidence=detection.get("confidence", 0.0),
            lat=detection.get("lat", 0.0),
            lng=detection.get("lng", 0.0),
            timestamp=detection.get("timestamp", ""),
            mission_id=mission_id,
        )
        self._retention_buffer.append(retained)

        return {
            "status": "RETAINED",
            "bytes_transmitted": 0,
            "state": self._state.value,
            "packet": None,
            "buffer_size": len(self._retention_buffer),
        }

    def _handle_event(self, detection: Dict[str, Any], mission_id: str) -> Dict[str, Any]:
        """EVENT: compact metadata packet transmission."""
        t_start = time.perf_counter()
        self._state = CommState.ACTIVATE

        if not self.link_available:
            self._stats.retained += 1
            self._state = CommState.INACTIVE
            return {
                "status": "LINK_UNAVAILABLE",
                "bytes_transmitted": 0,
                "state": self._state.value,
                "packet": None,
            }

        self._state = CommState.TRANSMIT
        packet = EventPacket(
            packet_id=self._next_packet_id("EVT"),
            mission_id=mission_id,
            target_type=detection.get("objectClass", "Unknown"),
            confidence=detection.get("confidence", 0.0),
            lat=detection.get("lat", 0.0),
            lng=detection.get("lng", 0.0),
            altitude_m=detection.get("altitudeM", 0.0),
            zone_name=detection.get("zoneName"),
            timestamp=detection.get("timestamp", ""),
        )
        bytes_tx = packet.byte_size()

        # Simulate latency
        self._state = CommState.VERIFY
        elapsed_ms = (time.perf_counter() - t_start) * 1000 + self._simulate_latency_ms
        self._stats.packets_sent += 1
        self._stats.bytes_transmitted += bytes_tx
        self._stats.events_transmitted += 1
        self._stats.transmit_durations_ms.append(elapsed_ms)
        self._stats.last_transmission_ms = elapsed_ms
        self._transmitted_events.append(packet)
        self._state = CommState.INACTIVE

        return {
            "status": "TRANSMITTED",
            "bytes_transmitted": bytes_tx,
            "state": self._state.value,
            "latency_ms": round(elapsed_ms, 3),
            "packet": packet.to_dict(),
        }

    def _handle_evidence(self, detection: Dict[str, Any], mission_id: str) -> Dict[str, Any]:
        """EVIDENCE: metadata + ROI evidence packet transmission."""
        t_start = time.perf_counter()
        self._state = CommState.ACTIVATE

        if not self.link_available:
            self._stats.retained += 1
            self._state = CommState.INACTIVE
            return {
                "status": "LINK_UNAVAILABLE",
                "bytes_transmitted": 0,
                "state": self._state.value,
                "packet": None,
            }

        self._state = CommState.TRANSMIT
        bbox = detection.get("normBbox", (0.0, 0.0, 0.1, 0.1))
        packet = EvidencePacket(
            packet_id=self._next_packet_id("EVI"),
            mission_id=mission_id,
            target_type=detection.get("objectClass", "Unknown"),
            confidence=detection.get("confidence", 0.0),
            lat=detection.get("lat", 0.0),
            lng=detection.get("lng", 0.0),
            altitude_m=detection.get("altitudeM", 0.0),
            zone_name=detection.get("zoneName"),
            timestamp=detection.get("timestamp", ""),
            roi_bbox=tuple(bbox),
            roi_resolution=(640, 480),
            frame_id=detection.get("frameId", 0),
        )
        bytes_tx = packet.byte_size()

        self._state = CommState.VERIFY
        elapsed_ms = (time.perf_counter() - t_start) * 1000 + self._simulate_latency_ms
        self._stats.packets_sent += 1
        self._stats.bytes_transmitted += bytes_tx
        self._stats.evidence_transmitted += 1
        self._stats.transmit_durations_ms.append(elapsed_ms)
        self._stats.last_transmission_ms = elapsed_ms
        self._transmitted_evidence.append(packet)
        self._state = CommState.INACTIVE

        return {
            "status": "TRANSMITTED",
            "bytes_transmitted": bytes_tx,
            "state": self._state.value,
            "latency_ms": round(elapsed_ms, 3),
            "packet": packet.to_dict(),
        }

    # ── Accessors ──────────────────────────────────────────────────────

    def get_transmitted_events(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [p.to_dict() for p in self._transmitted_events]

    def get_transmitted_evidence(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [p.to_dict() for p in self._transmitted_evidence]

    def get_retained_buffer(self) -> List[Dict[str, Any]]:
        with self._lock:
            return [
                {
                    "detectionId": r.detection_id,
                    "reason": r.reason,
                    "targetType": r.target_type,
                    "confidence": r.confidence,
                    "lat": r.lat,
                    "lng": r.lng,
                    "timestamp": r.timestamp,
                    "missionId": r.mission_id,
                }
                for r in self._retention_buffer
            ]

    def set_link_available(self, available: bool):
        with self._lock:
            self.link_available = available

    def reset_stats(self):
        with self._lock:
            self._stats = CommStats()
            self._retention_buffer.clear()
            self._transmitted_events.clear()
            self._transmitted_evidence.clear()
            self._packet_counter = 0
            self._state = CommState.INACTIVE
