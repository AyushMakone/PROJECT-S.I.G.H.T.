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
} from '../../types';
import {
  INITIAL_MISSION,
  INITIAL_MISSION_CARD,
  INITIAL_TELEMETRY,
  INITIAL_GOVERNOR_DECISION,
  INITIAL_COMMUNICATION_STATUS,
  INITIAL_METRICS,
  INITIAL_DETECTIONS,
  INITIAL_TIMELINE,
  INITIAL_EVIDENCE,
  INITIAL_WAYPOINTS,
  INITIAL_PRIORITY_ZONES
} from '../../mock/missionData';

type Listener<T> = (data: T) => void;

class SimulationEngine {
  private isRunning: boolean = false;
  private timer: any = null;
  private currentStep: number = 0;

  // State
  private mission: Mission = { ...INITIAL_MISSION };
  private missionCard: MissionCard = { ...INITIAL_MISSION_CARD };
  private telemetry: Telemetry = { ...INITIAL_TELEMETRY };
  private governorDecision: GovernorDecision = { ...INITIAL_GOVERNOR_DECISION };
  private communicationStatus: CommunicationStatus = { ...INITIAL_COMMUNICATION_STATUS };
  private metrics: MetricSummary = { ...INITIAL_METRICS };
  private detections: Detection[] = [...INITIAL_DETECTIONS];
  private timeline: TimelineEvent[] = [...INITIAL_TIMELINE];
  private evidence: EvidenceItem[] = [...INITIAL_EVIDENCE];
  private waypoints: Waypoint[] = [...INITIAL_WAYPOINTS];
  private priorityZones: PriorityZone[] = [...INITIAL_PRIORITY_ZONES];

  // Listeners
  private listeners: {
    telemetry: Set<Listener<Telemetry>>;
    governor: Set<Listener<GovernorDecision>>;
    communication: Set<Listener<CommunicationStatus>>;
    metrics: Set<Listener<MetricSummary>>;
    detections: Set<Listener<Detection[]>>;
    timeline: Set<Listener<TimelineEvent[]>>;
    mission: Set<Listener<Mission>>;
    evidence: Set<Listener<EvidenceItem[]>>;
    status: Set<Listener<boolean>>;
  } = {
    telemetry: new Set(),
    governor: new Set(),
    communication: new Set(),
    metrics: new Set(),
    detections: new Set(),
    timeline: new Set(),
    mission: new Set(),
    evidence: new Set(),
    status: new Set()
  };

  constructor() {
    // Start running simulation by default for an active operational feel
    this.start();
  }

  // Getters
  public getMission(): Mission { return this.mission; }
  public getMissionCard(): MissionCard { return this.missionCard; }
  public getTelemetry(): Telemetry { return this.telemetry; }
  public getGovernorDecision(): GovernorDecision { return this.governorDecision; }
  public getCommunicationStatus(): CommunicationStatus { return this.communicationStatus; }
  public getMetrics(): MetricSummary { return this.metrics; }
  public getDetections(): Detection[] { return this.detections; }
  public getTimeline(): TimelineEvent[] { return this.timeline; }
  public getEvidence(): EvidenceItem[] { return this.evidence; }
  public getWaypoints(): Waypoint[] { return this.waypoints; }
  public getPriorityZones(): PriorityZone[] { return this.priorityZones; }
  public getIsRunning(): boolean { return this.isRunning; }

  // Subscriptions
  public onTelemetry(fn: Listener<Telemetry>): () => void {
    this.listeners.telemetry.add(fn);
    fn(this.telemetry);
    return () => this.listeners.telemetry.delete(fn);
  }

  public onGovernor(fn: Listener<GovernorDecision>): () => void {
    this.listeners.governor.add(fn);
    fn(this.governorDecision);
    return () => this.listeners.governor.delete(fn);
  }

  public onCommunication(fn: Listener<CommunicationStatus>): () => void {
    this.listeners.communication.add(fn);
    fn(this.communicationStatus);
    return () => this.listeners.communication.delete(fn);
  }

  public onMetrics(fn: Listener<MetricSummary>): () => void {
    this.listeners.metrics.add(fn);
    fn(this.metrics);
    return () => this.listeners.metrics.delete(fn);
  }

  public onDetections(fn: Listener<Detection[]>): () => void {
    this.listeners.detections.add(fn);
    fn(this.detections);
    return () => this.listeners.detections.delete(fn);
  }

  public onTimeline(fn: Listener<TimelineEvent[]>): () => void {
    this.listeners.timeline.add(fn);
    fn(this.timeline);
    return () => this.listeners.timeline.delete(fn);
  }

  public onMission(fn: Listener<Mission>): () => void {
    this.listeners.mission.add(fn);
    fn(this.mission);
    return () => this.listeners.mission.delete(fn);
  }

  public onEvidence(fn: Listener<EvidenceItem[]>): () => void {
    this.listeners.evidence.add(fn);
    fn(this.evidence);
    return () => this.listeners.evidence.delete(fn);
  }

  public onRunningChange(fn: Listener<boolean>): () => void {
    this.listeners.status.add(fn);
    fn(this.isRunning);
    return () => this.listeners.status.delete(fn);
  }

  // Simulation Controls
  public start(): void {
    if (this.isRunning) return;
    this.isRunning = true;
    this.notifyStatus();
    this.timer = setInterval(() => this.tick(), 1500);
  }

  public pause(): void {
    if (!this.isRunning) return;
    this.isRunning = false;
    this.notifyStatus();
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
  }

  public toggle(): void {
    if (this.isRunning) {
      this.pause();
    } else {
      this.start();
    }
  }

  public step(): void {
    this.tick();
  }

  public reset(): void {
    this.pause();
    this.currentStep = 0;
    this.mission = { ...INITIAL_MISSION };
    this.missionCard = { ...INITIAL_MISSION_CARD };
    this.telemetry = { ...INITIAL_TELEMETRY };
    this.governorDecision = { ...INITIAL_GOVERNOR_DECISION };
    this.communicationStatus = { ...INITIAL_COMMUNICATION_STATUS };
    this.metrics = { ...INITIAL_METRICS };
    this.detections = [...INITIAL_DETECTIONS];
    this.timeline = [...INITIAL_TIMELINE];
    this.evidence = [...INITIAL_EVIDENCE];
    this.notifyAll();
  }

  public updateMissionCard(newCard: MissionCard): void {
    this.missionCard = { ...newCard };
    this.mission = {
      ...this.mission,
      id: newCard.missionId,
      card: { ...newCard }
    };
    
    // Add timeline event
    this.addTimelineEvent({
      id: `tl-mc-${Date.now()}`,
      timestamp: this.getCurrentUtc(),
      category: 'MISSION',
      title: `Mission Card Updated: ${newCard.missionId}`,
      detail: `Objective: ${newCard.objective}. Policy: ${newCard.communicationPolicy}.`,
      level: 'info'
    });

    this.notifyMission();
  }

  private getCurrentUtc(): string {
    const now = new Date();
    const h = String(now.getUTCHours()).padStart(2, '0');
    const m = String(now.getUTCMinutes()).padStart(2, '0');
    const s = String(now.getUTCSeconds()).padStart(2, '0');
    return `${h}:${m}:${s} UTC`;
  }

  // Main simulation tick loop
  private tick(): void {
    this.currentStep++;
    const nowStr = this.getCurrentUtc();

    // 1. Move UAV slightly along flight path (loitering between waypoint 2 and priority zone)
    const angle = (this.currentStep * 0.08) % (2 * Math.PI);
    const radiusLat = 0.0035;
    const radiusLng = 0.0045;
    const centerLat = 34.0620;
    const centerLng = -117.8050;

    const newLat = Number((centerLat + Math.sin(angle) * radiusLat).toFixed(5));
    const newLng = Number((centerLng + Math.cos(angle) * radiusLng).toFixed(5));
    
    // Compute heading in degrees based on movement tangent
    const headingDeg = Math.round(((angle + Math.PI / 2) * 180 / Math.PI) % 360);
    const headings = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
    const headingIdx = Math.floor(((headingDeg + 22.5) % 360) / 45);
    const headingStr = headings[headingIdx];

    // Slight altitude and speed fluctuations
    const altJitter = Number((84 + Math.sin(this.currentStep * 0.2) * 2.5).toFixed(1));
    const speedJitter = Number((12 + Math.cos(this.currentStep * 0.15) * 1.2).toFixed(1));
    const battRemaining = Math.max(15, Number((82 - (this.currentStep * 0.015)).toFixed(1)));

    this.telemetry = {
      ...this.telemetry,
      lat: newLat,
      lng: newLng,
      heading: headingStr,
      headingDegrees: headingDeg,
      altitude: altJitter,
      speed: speedJitter,
      battery: battRemaining,
      batteryVoltage: Number((24.6 - (100 - battRemaining) * 0.04).toFixed(2)),
      yaw: headingDeg
    };
    this.notifyTelemetry();

    // 2. Baseline metrics always accumulate continuously (simulating unmanaged continuous transmission)
    this.metrics = {
      ...this.metrics,
      baselineBytes: this.metrics.baselineBytes + 48200, // ~48KB/tick continuous
      baselinePackets: this.metrics.baselinePackets + 6,
      baselineDurationSec: this.metrics.baselineDurationSec + 2
    };

    // 3. Handle active transmission pulse expiration
    if (this.communicationStatus.status === 'ACTIVE') {
      this.communicationStatus = {
        ...this.communicationStatus,
        status: 'INACTIVE'
      };
      this.notifyCommunication();
    }

    // 4. Periodically simulate detections and Governor decisions
    if (this.currentStep % 8 === 0) {
      this.simulateEventTrigger(nowStr);
    }

    this.notifyMetrics();
  }

  private simulateEventTrigger(timestamp: string): void {
    const cycle = (Math.floor(this.currentStep / 8)) % 4;

    if (cycle === 0) {
      // EVENT: Vehicle in Priority Zone
      const newDetection: Detection = {
        id: `DET-${Date.now().toString().slice(-4)}`,
        object: 'Vehicle',
        confidence: 89,
        timestamp,
        lat: 34.0628,
        lng: -117.8032,
        locationName: 'North Perimeter Boundary',
        zone: 'Priority Zone Alpha',
        insidePriorityZone: true,
        persistence: 3,
        governorDecision: 'EVENT'
      };
      this.detections = [newDetection, ...this.detections.slice(0, 19)];

      this.governorDecision = {
        decision: 'EVENT',
        reason: 'Mission-relevant vehicle detected inside priority zone with required persistence.',
        action: 'Transmit compact event metadata.',
        evaluatedConditions: {
          communicationAvailable: true,
          batteryAboveThreshold: true,
          relevantObject: true,
          insidePriorityZone: true,
          persistenceSatisfied: true,
          evidenceRequired: this.missionCard.evidence === 'Enabled'
        },
        timestamp,
        targetId: newDetection.id,
        targetType: 'Vehicle'
      };

      // Brief communication burst
      this.communicationStatus = {
        ...this.communicationStatus,
        status: 'ACTIVE',
        packets: this.communicationStatus.packets + 1,
        bytes: this.communicationStatus.bytes + 480, // Compact metadata packet
        transmissionDurationSec: this.communicationStatus.transmissionDurationSec + 1,
        lastTransmission: timestamp,
        lastPacketType: 'EVENT'
      };

      this.metrics = {
        ...this.metrics,
        sightBytes: this.metrics.sightBytes + 480,
        sightPackets: this.metrics.sightPackets + 1,
        sightDurationSec: this.metrics.sightDurationSec + 1
      };

      this.addTimelineEvent({
        id: `tl-${Date.now()}`,
        timestamp,
        category: 'GOVERNOR',
        title: 'Governor → EVENT (Target: Vehicle)',
        detail: 'Zone Alpha breach verified. Event metadata packet transmitted.',
        level: 'warning'
      });
    } else if (cycle === 1) {
      // RETAIN: Person outside priority zone
      const newDetection: Detection = {
        id: `DET-${Date.now().toString().slice(-4)}`,
        object: 'Person',
        confidence: 76,
        timestamp,
        lat: 34.0558,
        lng: -117.8172,
        locationName: 'Outer Buffer Perimeter',
        zone: 'Outside Priority Zone',
        insidePriorityZone: false,
        persistence: 2,
        governorDecision: 'RETAIN'
      };
      this.detections = [newDetection, ...this.detections.slice(0, 19)];

      this.governorDecision = {
        decision: 'RETAIN',
        reason: 'Mission-relevant object detected outside designated priority zones.',
        action: 'Cache detection metadata in edge NVMe buffer. Hold RF transmission.',
        evaluatedConditions: {
          communicationAvailable: true,
          batteryAboveThreshold: true,
          relevantObject: true,
          insidePriorityZone: false,
          persistenceSatisfied: true,
          evidenceRequired: false
        },
        timestamp,
        targetId: newDetection.id,
        targetType: 'Person'
      };

      this.addTimelineEvent({
        id: `tl-${Date.now()}`,
        timestamp,
        category: 'GOVERNOR',
        title: 'Governor → RETAIN (Target: Person)',
        detail: 'Target outside priority zone. Cached locally. RF link remains silent.',
        level: 'info'
      });
    } else if (cycle === 2) {
      // SUPPRESS: Animal detected
      const newDetection: Detection = {
        id: `DET-${Date.now().toString().slice(-4)}`,
        object: 'Animal',
        confidence: 93,
        timestamp,
        lat: 34.0520,
        lng: -117.8210,
        locationName: 'Open Terrain Scrub',
        zone: 'Outside Mission Relevance',
        insidePriorityZone: false,
        persistence: 4,
        governorDecision: 'SUPPRESS'
      };
      this.detections = [newDetection, ...this.detections.slice(0, 19)];

      this.governorDecision = {
        decision: 'SUPPRESS',
        reason: 'Detected target class (Animal) is not specified in Mission Card relevant objects.',
        action: 'Discard detection at edge. Zero RF emissions.',
        evaluatedConditions: {
          communicationAvailable: true,
          batteryAboveThreshold: true,
          relevantObject: false,
          insidePriorityZone: false,
          persistenceSatisfied: true,
          evidenceRequired: false
        },
        timestamp,
        targetId: newDetection.id,
        targetType: 'Animal'
      };

      this.addTimelineEvent({
        id: `tl-${Date.now()}`,
        timestamp,
        category: 'GOVERNOR',
        title: 'Governor → SUPPRESS (Target: Animal)',
        detail: 'Non-mission entity filtered at edge. RF emissions: 0 bytes.',
        level: 'info'
      });
    } else {
      // EVIDENCE: High-priority intrusion requiring visual snapshot
      if (this.missionCard.evidence !== 'Disabled') {
        const newEvidence: EvidenceItem = {
          id: `EVD-${Date.now().toString().slice(-4)}`,
          timestamp,
          detection: 'Vehicle',
          confidence: 96,
          location: 'East Access Gate Checkpoint',
          coordinates: { lat: 34.0538, lng: -117.8080 },
          reason: 'Mission card requires evidence capture for Sector East vehicle activity.',
          evidenceStatus: 'STORED_LOCALLY',
          localRetentionStatus: 'EDGE_NVME_STORED',
          transmissionStatus: 'HELD_SILENT',
          fileSizeKb: 1540
        };
        this.evidence = [newEvidence, ...this.evidence.slice(0, 9)];
        this.notifyEvidence();
      }

      this.governorDecision = {
        decision: 'EVENT',
        reason: 'Mission-relevant vehicle detected inside priority zone with required persistence.',
        action: 'Transmit compact event metadata.',
        evaluatedConditions: {
          communicationAvailable: true,
          batteryAboveThreshold: true,
          relevantObject: true,
          insidePriorityZone: true,
          persistenceSatisfied: true,
          evidenceRequired: this.missionCard.evidence === 'Enabled'
        },
        timestamp,
        targetType: 'Vehicle'
      };
    }

    this.notifyDetections();
    this.notifyGovernor();
    this.notifyCommunication();
  }

  private addTimelineEvent(event: TimelineEvent): void {
    this.timeline = [event, ...this.timeline.slice(0, 24)];
    this.notifyTimeline();
  }

  // Notifiers
  private notifyTelemetry(): void {
    this.listeners.telemetry.forEach(fn => fn(this.telemetry));
  }
  private notifyGovernor(): void {
    this.listeners.governor.forEach(fn => fn(this.governorDecision));
  }
  private notifyCommunication(): void {
    this.listeners.communication.forEach(fn => fn(this.communicationStatus));
  }
  private notifyMetrics(): void {
    this.listeners.metrics.forEach(fn => fn(this.metrics));
  }
  private notifyDetections(): void {
    this.listeners.detections.forEach(fn => fn(this.detections));
  }
  private notifyTimeline(): void {
    this.listeners.timeline.forEach(fn => fn(this.timeline));
  }
  private notifyMission(): void {
    this.listeners.mission.forEach(fn => fn(this.mission));
  }
  private notifyEvidence(): void {
    this.listeners.evidence.forEach(fn => fn(this.evidence));
  }
  private notifyStatus(): void {
    this.listeners.status.forEach(fn => fn(this.isRunning));
  }
  private notifyAll(): void {
    this.notifyTelemetry();
    this.notifyGovernor();
    this.notifyCommunication();
    this.notifyMetrics();
    this.notifyDetections();
    this.notifyTimeline();
    this.notifyMission();
    this.notifyEvidence();
    this.notifyStatus();
  }
}

// Singleton instance
export const simulationEngine = new SimulationEngine();
