// PROJECT S.I.G.H.T. Core Type Definitions

export type GovernorState = 'SUPPRESS' | 'RETAIN' | 'EVENT' | 'EVIDENCE';

export type ObjectClass = 'Person' | 'Vehicle' | 'Animal' | 'Vessel' | 'Aircraft';

export interface EvaluatedConditions {
  communicationAvailable: boolean;
  batteryAboveThreshold: boolean;
  relevantObject: boolean;
  insidePriorityZone: boolean;
  persistenceSatisfied: boolean;
  evidenceRequired: boolean;
}

export interface GovernorDecision {
  decision: GovernorState;
  reason: string;
  action: string;
  evaluatedConditions: EvaluatedConditions;
  timestamp: string;
  targetId?: string;
  targetType?: ObjectClass;
}

export interface MissionCard {
  missionId: string;
  objective: string;
  uavId: string;
  relevantObjects: ObjectClass[];
  persistence: string; // e.g. "2 frames"
  persistenceFrames: number;
  priorityZones: string[];
  evidence: 'Enabled' | 'Disabled' | 'On-Demand';
  communicationPolicy: 'EVENT ONLY' | 'EVENT & EVIDENCE' | 'SILENT' | 'ADAPTIVE';
  batteryRthThreshold: string; // e.g. "20%"
  batteryRthPercent: number;
  description?: string;
}

export interface Mission {
  id: string;
  name: string;
  status: 'ACTIVE' | 'PLANNED' | 'COMPLETED' | 'ABORTED';
  uavId: string;
  card: MissionCard;
  startTime: string;
  durationSeconds: number;
}

export interface Coordinates {
  lat: number;
  lng: number;
}

export interface Waypoint {
  id: string;
  name: string;
  lat: number;
  lng: number;
  altitude: number;
  sequence: number;
  isHome?: boolean;
  isPriorityZoneAnchor?: boolean;
}

export interface PriorityZone {
  id: string;
  name: string;
  polygon: [number, number][]; // Lat, Lng pairs
  fillColor?: string;
  description: string;
}

export interface Detection {
  id: string;
  object: ObjectClass;
  confidence: number; // 0-100%
  timestamp: string;
  lat: number;
  lng: number;
  locationName: string;
  zone: string;
  insidePriorityZone: boolean;
  persistence: number; // Frame count
  governorDecision: GovernorState;
  frameImageUrl?: string;
}

export interface Telemetry {
  altitude: number; // in meters (e.g. 84)
  speed: number; // in m/s (e.g. 12)
  heading: string; // e.g. "NE"
  headingDegrees: number; // 0-360
  battery: number; // percentage (e.g. 82)
  batteryVoltage: number; // e.g. 24.6V
  gpsStatus: 'FIXED' | 'NO_FIX' | 'ACQUIRING';
  gpsSatellites: number;
  hdop: number;
  lat: number;
  lng: number;
  flightMode: 'AUTO_MISSION' | 'LOITER' | 'RETURN_TO_HOME' | 'MANUAL';
  linkStatus: 'ONLINE' | 'DEGRADED' | 'LOST';
  rssi: number; // -dBm
  pitch: number;
  roll: number;
  yaw: number;
  climbRate: number; // m/s
  systemStatus: 'ONLINE' | 'STANDBY' | 'WARNING' | 'EMERGENCY';
}

export interface CommunicationStatus {
  status: 'INACTIVE' | 'ACTIVE';
  packets: number;
  bytes: number; // in bytes or KB display
  transmissionDurationSec: number;
  lastTransmission: string;
  lastPacketType: 'EVENT' | 'EVIDENCE' | 'NONE';
  channelFrequency: string; // e.g. "915 MHz"
  snr: number; // dB
  dutyCyclePercent: number;
  rfSilencePercent: number;
}

export interface MetricSummary {
  baselineBytes: number;
  baselinePackets: number;
  baselineDurationSec: number;
  sightBytes: number;
  sightPackets: number;
  sightDurationSec: number;
}

export interface TimelineEvent {
  id: string;
  timestamp: string;
  category: 'MISSION' | 'FLIGHT' | 'DETECTION' | 'GOVERNOR' | 'COMMUNICATION';
  title: string;
  detail?: string;
  level: 'info' | 'success' | 'warning' | 'alert';
}

export interface EvidenceItem {
  id: string;
  timestamp: string;
  detection: ObjectClass;
  confidence: number;
  location: string;
  coordinates: Coordinates;
  reason: string;
  evidenceStatus: 'CAPTURED' | 'PENDING' | 'TRANSMITTED' | 'STORED_LOCALLY';
  localRetentionStatus: 'EDGE_NVME_STORED' | 'BUFFERED_RAM' | 'COMPRESSED';
  transmissionStatus: 'HELD_SILENT' | 'COMPLETED' | 'QUEUED_FOR_RTH';
  fileSizeKb: number;
  previewThumbnail?: string;
}
