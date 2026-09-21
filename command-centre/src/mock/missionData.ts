import {
  Mission,
  MissionCard,
  Telemetry,
  Detection,
  GovernorDecision,
  CommunicationStatus,
  MetricSummary,
  TimelineEvent,
  EvidenceItem,
  Waypoint,
  PriorityZone
} from '../types';

export const INITIAL_MISSION_CARD: MissionCard = {
  missionId: 'SIGHT-M01',
  objective: 'Perimeter Surveillance',
  uavId: 'SIGHT-UAV-01',
  relevantObjects: ['Person', 'Vehicle'],
  persistence: '2 frames',
  persistenceFrames: 2,
  priorityZones: [],
  evidence: 'Disabled',
  communicationPolicy: 'EVENT ONLY',
  batteryRthThreshold: '20%',
  batteryRthPercent: 20,
  description: 'Autonomous stealth perimeter reconnaissance over military testing ground facility. Transmit only confirmed high-persistence targets in designated priority hot zones.'
};

export const ALTERNATE_MISSION_CARDS: MissionCard[] = [
  INITIAL_MISSION_CARD,
  {
    missionId: 'SIGHT-M02',
    objective: 'Border Sector Reconnaissance',
    uavId: 'SIGHT-UAV-01',
    relevantObjects: ['Vehicle', 'Person', 'Vessel'],
    persistence: '3 frames',
    persistenceFrames: 3,
    priorityZones: [],
    evidence: 'Enabled',
    communicationPolicy: 'EVENT & EVIDENCE',
    batteryRthThreshold: '25%',
    batteryRthPercent: 25,
    description: 'High-altitude stealth sector monitor with optical snapshot capture enabled for high-confidence border intrusion events.'
  },
  {
    missionId: 'SIGHT-M03',
    objective: 'Critical Infrastructure Silent Patrol',
    uavId: 'SIGHT-UAV-02',
    relevantObjects: ['Person', 'Vehicle', 'Aircraft'],
    persistence: '4 frames',
    persistenceFrames: 4,
    priorityZones: [],
    evidence: 'On-Demand',
    communicationPolicy: 'SILENT',
    batteryRthThreshold: '30%',
    batteryRthPercent: 30,
    description: 'Zero RF emission mandate during operational transit. All detections retained to edge NVMe storage until physical recovery or ground ping.'
  }
];

export const INITIAL_MISSION: Mission = {
  id: 'SIGHT-M01',
  name: 'Perimeter Surveillance Alpha',
  status: 'ACTIVE',
  uavId: 'SIGHT-UAV-01',
  card: INITIAL_MISSION_CARD,
  startTime: '19:41:00 UTC',
  durationSeconds: 945
};

// Base coordinates around a tactical proving ground / facility
export const BASE_CENTER = { lat: 34.0522, lng: -117.8247 };

export const INITIAL_WAYPOINTS: Waypoint[] = [
  { id: 'wp-0', name: 'HOME', lat: 34.0522, lng: -117.8247, altitude: 0, sequence: 0, isHome: true },
  { id: 'wp-1', name: 'WAYPOINT 1', lat: 34.0585, lng: -117.8205, altitude: 75, sequence: 1 },
  { id: 'wp-2', name: 'WAYPOINT 2', lat: 34.0645, lng: -117.8130, altitude: 84, sequence: 2 },
  { id: 'wp-3', name: 'PRIORITY ZONE ALPHA', lat: 34.0620, lng: -117.8010, altitude: 84, sequence: 3, isPriorityZoneAnchor: true },
  { id: 'wp-4', name: 'WAYPOINT 3', lat: 34.0540, lng: -117.8060, altitude: 80, sequence: 4 }
];

export const INITIAL_PRIORITY_ZONES: PriorityZone[] = [
  {
    id: 'zone-alpha',
    name: 'Priority Zone Alpha (North Ridge)',
    polygon: [
      [34.0590, -117.8090],
      [34.0665, -117.8070],
      [34.0650, -117.7950],
      [34.0575, -117.7970]
    ],
    fillColor: '#ef4444',
    description: 'High-security restricted perimeter. Immediate target verification required.'
  },
  {
    id: 'zone-beta',
    name: 'Priority Zone Beta (East Gate)',
    polygon: [
      [34.0510, -117.8120],
      [34.0560, -117.8100],
      [34.0545, -117.8020],
      [34.0495, -117.8040]
    ],
    fillColor: '#f59e0b',
    description: 'Perimeter access road. Monitored for unannounced vehicular movement.'
  }
];

export const INITIAL_TELEMETRY: Telemetry = {
  hasTelemetry: true,
  altitude: 84,
  speed: 12,
  heading: 'NE',
  headingDegrees: 45,
  battery: 82,
  batteryVoltage: 24.6,
  gpsStatus: 'FIXED',
  gpsSatellites: 18,
  hdop: 0.75,
  lat: 34.0622,
  lng: -117.8045,
  flightMode: 'AUTO_MISSION',
  linkStatus: 'ONLINE',
  rssi: -68,
  pitch: 2.1,
  roll: -1.4,
  yaw: 45.0,
  climbRate: 0.1,
  systemStatus: 'ONLINE'
};

export const INITIAL_GOVERNOR_DECISION: GovernorDecision = {
  decision: 'EVENT',
  reason: 'Mission-relevant vehicle detected inside priority zone with required persistence.',
  action: 'Transmit compact event metadata.',
  evaluatedConditions: {
    communicationAvailable: true,
    batteryAboveThreshold: true,
    relevantObject: true,
    insidePriorityZone: true,
    persistenceSatisfied: true,
    evidenceRequired: false
  },
  timestamp: '19:42:09 UTC',
  targetId: 'DET-2026-089',
  targetType: 'Vehicle'
};

export const INITIAL_COMMUNICATION_STATUS: CommunicationStatus = {
  status: 'INACTIVE',
  packets: 23,
  bytes: 190464, // 186 KB
  transmissionDurationSec: 41,
  lastTransmission: '19:42:09 UTC',
  lastPacketType: 'EVENT',
  channelFrequency: '915 MHz FHSS',
  snr: 28.4,
  dutyCyclePercent: 4.3,
  rfSilencePercent: 95.7
};

export const INITIAL_METRICS: MetricSummary = {
  baselineBytes: 13002342, // ~12.4 MB continuous streaming
  baselinePackets: 1840,
  baselineDurationSec: 620,
  sightBytes: 190464, // 186 KB
  sightPackets: 23,
  sightDurationSec: 41
};

export const INITIAL_DETECTIONS: Detection[] = [
  {
    id: 'DET-001',
    object: 'Vehicle',
    confidence: 87,
    timestamp: '19:42:08 UTC',
    lat: 34.0621,
    lng: -117.8038,
    locationName: 'Sector Alpha Access Road',
    zone: 'Priority Zone Alpha',
    insidePriorityZone: true,
    persistence: 3,
    governorDecision: 'EVENT'
  },
  {
    id: 'DET-002',
    object: 'Person',
    confidence: 72,
    timestamp: '19:43:14 UTC',
    lat: 34.0572,
    lng: -117.8184,
    locationName: 'Buffer Zone West',
    zone: 'Outside Priority Zone',
    insidePriorityZone: false,
    persistence: 2,
    governorDecision: 'RETAIN'
  },
  {
    id: 'DET-003',
    object: 'Animal',
    confidence: 91,
    timestamp: '19:44:02 UTC',
    lat: 34.0531,
    lng: -117.8220,
    locationName: 'Canyon Scrub Brush',
    zone: 'Outside Mission Relevance',
    insidePriorityZone: false,
    persistence: 5,
    governorDecision: 'SUPPRESS'
  },
  {
    id: 'DET-004',
    object: 'Vehicle',
    confidence: 94,
    timestamp: '19:46:18 UTC',
    lat: 34.0535,
    lng: -117.8075,
    locationName: 'Perimeter East Gate Approach',
    zone: 'Priority Zone Beta',
    insidePriorityZone: true,
    persistence: 4,
    governorDecision: 'EVENT'
  },
  {
    id: 'DET-005',
    object: 'Person',
    confidence: 64,
    timestamp: '19:47:30 UTC',
    lat: 34.0655,
    lng: -117.8015,
    locationName: 'North Ridge Fence Line',
    zone: 'Priority Zone Alpha',
    insidePriorityZone: true,
    persistence: 1, // < 2 frames required
    governorDecision: 'RETAIN'
  }
];

export const INITIAL_TIMELINE: TimelineEvent[] = [
  {
    id: 'tl-1',
    timestamp: '19:41:00 UTC',
    category: 'MISSION',
    title: 'Mission started',
    detail: 'Mission SIGHT-M01 initialized. Flight plan uploaded.',
    level: 'info'
  },
  {
    id: 'tl-2',
    timestamp: '19:41:12 UTC',
    category: 'FLIGHT',
    title: 'UAV takeoff',
    detail: 'SIGHT-UAV-01 airborne. Climbed to 84m AGL.',
    level: 'success'
  },
  {
    id: 'tl-3',
    timestamp: '19:42:08 UTC',
    category: 'DETECTION',
    title: 'Vehicle detected',
    detail: 'Target classified: Vehicle (87% confidence, 3 frames persistence).',
    level: 'warning'
  },
  {
    id: 'tl-4',
    timestamp: '19:42:09 UTC',
    category: 'GOVERNOR',
    title: 'Governor → EVENT',
    detail: 'Target satisfied priority zone and persistence criteria.',
    level: 'info'
  },
  {
    id: 'tl-5',
    timestamp: '19:42:09 UTC',
    category: 'COMMUNICATION',
    title: 'Event packet transmitted',
    detail: 'Compact telemetry/target metadata burst (420 bytes). Link returned to INACTIVE.',
    level: 'success'
  },
  {
    id: 'tl-6',
    timestamp: '19:43:14 UTC',
    category: 'DETECTION',
    title: 'Person detected',
    detail: 'Target classified: Person (72% confidence, Buffer Zone West).',
    level: 'info'
  },
  {
    id: 'tl-7',
    timestamp: '19:43:15 UTC',
    category: 'GOVERNOR',
    title: 'Governor → RETAIN',
    detail: 'Target outside priority zone. Cached in edge NVMe without RF emission.',
    level: 'warning'
  },
  {
    id: 'tl-8',
    timestamp: '19:44:02 UTC',
    category: 'DETECTION',
    title: 'Animal detected',
    detail: 'Target classified: Animal (91% confidence). Not in mission relevant objects.',
    level: 'info'
  },
  {
    id: 'tl-9',
    timestamp: '19:44:03 UTC',
    category: 'GOVERNOR',
    title: 'Governor → SUPPRESS',
    detail: 'Non-mission target discarded at edge. Zero RF emissions.',
    level: 'info'
  }
];

export const INITIAL_EVIDENCE: EvidenceItem[] = [
  {
    id: 'EVD-101',
    timestamp: '19:42:08 UTC',
    detection: 'Vehicle',
    confidence: 87,
    location: 'Sector Alpha Access Road (34.0621° N, 117.8038° W)',
    coordinates: { lat: 34.0621, lng: -117.8038 },
    reason: 'Confirmed Vehicle breach inside Priority Zone Alpha with 3-frame persistence.',
    evidenceStatus: 'STORED_LOCALLY',
    localRetentionStatus: 'EDGE_NVME_STORED',
    transmissionStatus: 'HELD_SILENT',
    fileSizeKb: 1420
  },
  {
    id: 'EVD-102',
    timestamp: '19:46:18 UTC',
    detection: 'Vehicle',
    confidence: 94,
    location: 'Perimeter East Gate Approach (34.0535° N, 117.8075° W)',
    coordinates: { lat: 34.0535, lng: -117.8075 },
    reason: 'Unidentified heavy vehicle approaching perimeter gate boundary.',
    evidenceStatus: 'STORED_LOCALLY',
    localRetentionStatus: 'EDGE_NVME_STORED',
    transmissionStatus: 'HELD_SILENT',
    fileSizeKb: 1680
  },
  {
    id: 'EVD-103',
    timestamp: '19:48:02 UTC',
    detection: 'Person',
    confidence: 83,
    location: 'Zone Alpha Fence Line (34.0642° N, 117.8021° W)',
    coordinates: { lat: 34.0642, lng: -117.8021 },
    reason: 'Dismounted personnel loitering adjacent to boundary sensor tripwire.',
    evidenceStatus: 'PENDING',
    localRetentionStatus: 'BUFFERED_RAM',
    transmissionStatus: 'QUEUED_FOR_RTH',
    fileSizeKb: 890
  }
];
