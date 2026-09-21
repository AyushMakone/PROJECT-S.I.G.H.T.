import { createContext, createElement, useCallback, useContext, useEffect, useState, type ReactNode } from 'react';
import {
  getRuntimeStatus,
  fetchMission,
  fetchGovernorState,
  fetchCommunicationStatus,
  fetchDetections,
  getDetectorStatus,
  getCameraStatus,
  checkBackendHealth,
  saveMission,
  ApiRequestError,
  connectSimulator as apiConnectSimulator,
  disconnectSimulator as apiDisconnectSimulator,
  armDrone,
  disarmDrone,
  takeoffDrone,
  landDrone,
  hoverDrone,
  moveDrone,
  setHeadingDrone,
  returnToHomeDrone,
  getFlightCommandLog,
  type BackendMissionCard,
  type RuntimeStatus,
  type DetectorStatus,
  type CameraStatus,
  type FlightCommandLogEntry
} from '../services/api';
import {
  Mission,
  MissionCard,
  Telemetry,
  GovernorDecision,
  CommunicationStatus,
  MetricSummary,
  Detection,
  TimelineEvent,
  EvidenceItem,
  Waypoint,
  PriorityZone,
  type ObjectClass
} from '../types';
export type RuntimeConnectionStatus = 'LIVE' | 'STALE' | 'OFFLINE';
export type MissionSource = 'LOADING' | 'LIVE' | 'FALLBACK' | 'UNAVAILABLE';
export type MissionSaveState = 'IDLE' | 'SAVING' | 'SAVED' | 'SAVE_FAILED';

export interface RuntimeErrors {
  backendError: string | null;
  telemetryError: string | null;
  missionError: string | null;
  governorError: string | null;
  communicationError: string | null;
}

const UNKNOWN_TELEMETRY: Telemetry = {
  hasTelemetry: false,
  altitude: 0,
  relativeAltitude: undefined,
  speed: 0,
  heading: '—',
  headingDegrees: 0,
  battery: 0,
  batteryVoltage: 0,
  gpsStatus: 'ACQUIRING',
  gpsSatellites: 0,
  hdop: 0,
  lat: 0,
  lng: 0,
  autopilot: 'NO DATA',
  vehicle: 'NO DATA',
  connectionState: 'DISCONNECTED',
  flightMode: 'NO DATA',
  linkStatus: 'LOST',
  rssi: 0,
  pitch: 0,
  roll: 0,
  yaw: 0,
  climbRate: 0,
  systemStatus: 'STANDBY',
  isArmed: false,
  timestamp: ''
};

const UNKNOWN_GOVERNOR: GovernorDecision = {
  decision: 'UNKNOWN',
  reason: 'Governor not connected. Waiting for Edge AI + Mission Context input.',
  action: 'No live decision available.',
  evaluatedConditions: {
    communicationAvailable: false,
    batteryAboveThreshold: false,
    relevantObject: false,
    insidePriorityZone: false,
    persistenceSatisfied: false,
    evidenceRequired: false
  },
  timestamp: 'NO DATA'
};

const UNKNOWN_COMMUNICATION: CommunicationStatus = {
  status: 'OFFLINE',
  packets: 0,
  bytes: 0,
  transmissionDurationSec: 0,
  lastTransmission: 'NO DATA',
  lastPacketType: 'NONE',
  channelFrequency: 'NO DATA',
  snr: 0,
  dutyCyclePercent: 0,
  rfSilencePercent: 0,
  linkAvailable: false
};

const EMPTY_METRICS: MetricSummary = {
  baselineBytes: 0,
  baselinePackets: 0,
  baselineDurationSec: 0,
  sightBytes: 0,
  sightPackets: 0,
  sightDurationSec: 0
};

const EMPTY_ERRORS: RuntimeErrors = {
  backendError: null,
  telemetryError: null,
  missionError: null,
  governorError: null,
  communicationError: null
};

const EMPTY_MISSION_CARD: MissionCard = {
  missionId: 'NO-LIVE-MISSION',
  objective: 'Mission unavailable',
  uavId: 'NO DATA',
  relevantObjects: [],
  persistence: 'NO DATA',
  persistenceFrames: 0,
  priorityZones: [],
  waypoints: [],
  evidence: 'Disabled',
  communicationPolicy: 'SILENT',
  batteryRthThreshold: 'NO DATA',
  batteryRthPercent: 0,
  description: 'No mission card has been loaded from the backend.'
};

const EMPTY_MISSION: Mission = {
  id: 'NO-LIVE-MISSION',
  name: 'Mission unavailable',
  status: 'PLANNED',
  uavId: 'NO DATA',
  card: EMPTY_MISSION_CARD,
  startTime: 'NO DATA',
  durationSeconds: 0
};

const toHeadingLabel = (heading: number | null | undefined): string => {
  if (typeof heading !== 'number' || Number.isNaN(heading)) return '—';
  const dirs = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
  const index = Math.round(((heading % 360) + 360) % 360 / 45) % 8;
  return dirs[index];
};

const isObjectClass = (value: string): value is ObjectClass =>
  ['Person', 'Vehicle', 'Animal', 'Vessel', 'Aircraft'].includes(value);

const normalizeMissionCard = (card: BackendMissionCard): MissionCard | null => {
  if (typeof card.missionId !== 'string' || typeof card.objective !== 'string') return null;

  const persistenceFrames = typeof card.persistenceFrames === 'number' ? card.persistenceFrames : 2;
  const batteryRthPercent = typeof card.batteryRthPercent === 'number' ? card.batteryRthPercent : 20;
  const relevantObjects = (card.relevantObjects ?? []).filter(isObjectClass);
  const priorityZones = (card.priorityZones ?? []).map((zone) => ({
    id: zone.id,
    name: zone.name,
    polygon: zone.polygon,
    description: zone.description ?? '',
    priority: zone.priority ?? 'HIGH',
    active: zone.active ?? true
  }));
  const waypoints = (card.waypoints ?? []).map((waypoint, index) => ({
    id: waypoint.id,
    name: waypoint.name ?? `WP${index + 1}`,
    lat: waypoint.lat,
    lng: waypoint.lon,
    altitude: waypoint.altitude ?? 20,
    acceptanceRadius: waypoint.acceptanceRadius ?? 10,
    sequence: index + 1
  }));
  const evidence = card.evidence === 'Enabled' || card.evidence === 'On-Demand' ? card.evidence : 'Disabled';
  const communicationPolicy = card.communicationPolicy === 'EVENT & EVIDENCE'
    || card.communicationPolicy === 'SILENT'
    || card.communicationPolicy === 'ADAPTIVE'
    ? card.communicationPolicy
    : 'EVENT ONLY';

  return {
    missionId: card.missionId,
    objective: card.objective,
    uavId: typeof card.uavId === 'string' ? card.uavId : 'SIGHT-UAV-01',
    relevantObjects,
    persistence: typeof card.persistence === 'string' ? card.persistence : `${persistenceFrames} frames`,
    persistenceFrames,
    priorityZones,
    waypoints,
    evidence,
    communicationPolicy,
    batteryRthThreshold: typeof card.batteryRthThreshold === 'string' ? card.batteryRthThreshold : `${batteryRthPercent}%`,
    batteryRthPercent,
    description: typeof card.description === 'string' ? card.description : undefined
  };
};

interface SimulationContextValue {
  mission: Mission;
  missionCard: MissionCard;
  telemetry: Telemetry;
  governor: GovernorDecision;
  communication: CommunicationStatus;
  metrics: MetricSummary;
  detections: Detection[];
  timeline: TimelineEvent[];
  evidence: EvidenceItem[];
  waypoints: Waypoint[];
  priorityZones: PriorityZone[];
  isRunning: boolean;
  connectionStatus: RuntimeConnectionStatus;
  simulatorMode: 'local' | 'cloud' | 'fallback';
  lastTelemetryTimestamp: string;
  backendConnected: boolean;
  isConnecting: boolean;
  errors: RuntimeErrors;
  missionLoading: boolean;
  missionSource: MissionSource;
  missionSaveState: MissionSaveState;
  missionSaveError: string | null;
  commandLog: FlightCommandLogEntry[];
  detectorStatus: DetectorStatus | null;
  cameraStatus: CameraStatus | null;
  connectSimulator: (mode?: 'local' | 'cloud' | 'fallback', host?: string, port?: number, endpoint?: string) => Promise<{ status: string; mode: string; isConnected: boolean }>;
  disconnectSimulator: () => Promise<boolean>;
  arm: typeof armDrone;
  disarm: typeof disarmDrone;
  takeoff: typeof takeoffDrone;
  land: typeof landDrone;
  hover: typeof hoverDrone;
  move: typeof moveDrone;
  setHeading: typeof setHeadingDrone;
  returnToHome: typeof returnToHomeDrone;
  saveMissionCard: (newCard: MissionCard) => Promise<void>;
  toggleSimulation: () => ReturnType<typeof takeoffDrone>;
  stepSimulation: () => ReturnType<typeof moveDrone>;
  resetSimulation: typeof returnToHomeDrone;
}

const SimulationContext = createContext<SimulationContextValue | null>(null);

export function SimulationProvider({ children }: { children: ReactNode }) {
  const [mission, setMission] = useState<Mission>({ ...EMPTY_MISSION });
  const [missionCard, setMissionCard] = useState<MissionCard>({ ...EMPTY_MISSION_CARD });
  const [telemetry, setTelemetry] = useState<Telemetry>({ ...UNKNOWN_TELEMETRY });
  const [governor, setGovernor] = useState<GovernorDecision>({ ...UNKNOWN_GOVERNOR });
  const [communication, setCommunication] = useState<CommunicationStatus>({ ...UNKNOWN_COMMUNICATION });
  const [metrics] = useState<MetricSummary>({ ...EMPTY_METRICS });
  const [liveDetections, setLiveDetections] = useState<Detection[]>([]);
  const [detectorStatus, setDetectorStatus] = useState<DetectorStatus | null>(null);
  const [cameraStatus, setCameraStatus] = useState<CameraStatus | null>(null);
  const [timeline] = useState<TimelineEvent[]>([]);
  const [evidence] = useState<EvidenceItem[]>([]);
  const [waypoints, setWaypoints] = useState<Waypoint[]>([]);
  const [priorityZones, setPriorityZones] = useState<PriorityZone[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<RuntimeConnectionStatus>('OFFLINE');
  const [simulatorMode, setSimulatorMode] = useState<'local' | 'cloud' | 'fallback'>('local');
  const [lastTelemetryTimestamp, setLastTelemetryTimestamp] = useState<string>('');
  const [isRunning, setIsRunning] = useState<boolean>(false);
  const [backendConnected, setBackendConnected] = useState<boolean>(false);
  const [isConnecting, setIsConnecting] = useState<boolean>(false);
  const [errors, setErrors] = useState<RuntimeErrors>({ ...EMPTY_ERRORS });
  const [missionLoading, setMissionLoading] = useState<boolean>(true);
  const [missionSource, setMissionSource] = useState<MissionSource>('LOADING');
  const [missionSaveState, setMissionSaveState] = useState<MissionSaveState>('IDLE');
  const [missionSaveError, setMissionSaveError] = useState<string | null>(null);
  const [commandLog, setCommandLog] = useState<FlightCommandLogEntry[]>([]);

  const normalizeDetection = useCallback((detection: Awaited<ReturnType<typeof fetchDetections>>[number]): Detection => ({
    id: detection.id,
    object: isObjectClass(detection.objectClass) ? detection.objectClass : 'Animal',
    objectClass: isObjectClass(detection.objectClass) ? detection.objectClass : undefined,
    confidence: detection.confidence,
    timestamp: detection.timestamp,
    lat: detection.lat,
    lng: detection.lng,
    locationName: detection.zoneName ?? 'UNCLASSIFIED',
    zone: detection.zoneName ?? 'Outside Priority Zone',
    insidePriorityZone: Boolean(detection.insidePriorityZone),
    persistence: detection.persistence,
    governorDecision: detection.governorDecision === 'SUPPRESS' || detection.governorDecision === 'RETAIN' || detection.governorDecision === 'EVENT' || detection.governorDecision === 'EVIDENCE'
      ? detection.governorDecision
      : 'RETAIN',
    normBbox: detection.normBbox,
    trackId: detection.trackId,
    altitudeM: detection.altitudeM,
    frameId: detection.frameId,
    source: detection.source,
    locationSource: detection.locationSource,
    targetGeolocationAvailable: detection.targetGeolocationAvailable
  }), []);

  const hydrateTelemetryFromStatus = useCallback((status: RuntimeStatus | null | undefined) => {
    if (!status) {
      setTelemetry({ ...UNKNOWN_TELEMETRY });
      setConnectionStatus('STALE');
      setIsRunning(false);
      return;
    }

    const hasData = Boolean(status.connected || status.heartbeat_received || status.altitude !== null || status.latitude !== null || status.longitude !== null || status.battery !== null);
    if (!hasData) {
      setTelemetry({ ...UNKNOWN_TELEMETRY });
      setConnectionStatus('STALE');
      setIsRunning(false);
      setBackendConnected(true);
      setErrors((prev) => ({ ...prev, telemetryError: 'Runtime telemetry is stale.' }));
      return;
    }
    const headingValue = typeof status.heading === 'number' ? status.heading : 0;

    setTelemetry((prev) => ({
      ...prev,
      hasTelemetry: hasData,
      relativeAltitude: typeof status.relative_altitude === 'number' ? status.relative_altitude : prev.relativeAltitude,
      lat: typeof status.latitude === 'number' ? status.latitude : prev.lat,
      lng: typeof status.longitude === 'number' ? status.longitude : prev.lng,
      altitude: typeof status.altitude === 'number' ? status.altitude : prev.altitude,
      speed: typeof status.ground_speed === 'number' ? status.ground_speed : prev.speed,
      heading: toHeadingLabel(headingValue),
      headingDegrees: headingValue,
      battery: typeof status.battery === 'number' ? status.battery : prev.battery,
      autopilot: typeof status.autopilot === 'string' && status.autopilot ? status.autopilot : prev.autopilot ?? 'NO DATA',
      vehicle: typeof status.vehicle === 'string' && status.vehicle ? status.vehicle : prev.vehicle ?? 'NO DATA',
      connectionState: typeof status.connection_state === 'string' && status.connection_state ? status.connection_state : prev.connectionState ?? 'DISCONNECTED',
      flightMode: typeof status.mode === 'string' ? status.mode : prev.flightMode,
      linkStatus: status.connected ? 'ONLINE' : 'LOST',
      systemStatus: status.connected ? 'ONLINE' : 'STANDBY',
      gpsStatus: status.gps_fix === 'FIXED' ? 'FIXED' : status.gps_fix === 'NO_FIX' ? 'NO_FIX' : 'ACQUIRING',
      gpsSatellites: typeof status.satellites === 'number' ? status.satellites : prev.gpsSatellites,
      pitch: typeof status.pitch === 'number' ? status.pitch : prev.pitch,
      roll: typeof status.roll === 'number' ? status.roll : prev.roll,
      yaw: typeof status.yaw === 'number' ? status.yaw : prev.yaw,
      isArmed: typeof status.armed === 'boolean' ? status.armed : prev.isArmed,
      timestamp: typeof status.timestamp === 'string' ? status.timestamp : prev.timestamp
    }));

    if (typeof status.timestamp === 'string') setLastTelemetryTimestamp(status.timestamp);
    setConnectionStatus(status.connected ? 'LIVE' : 'STALE');
    setBackendConnected(true);
    setIsRunning(Boolean(status.connected));
    setErrors((prev) => ({ ...prev, telemetryError: status.connected ? null : 'Runtime telemetry is stale.' }));
  }, []);

  useEffect(() => {
    let cancelled = false;

    const loadMission = async () => {
      try {
        const cardData = await fetchMission();
        if (cancelled) return;
        const normalizedCard = cardData && normalizeMissionCard(cardData);
        if (!normalizedCard) throw new Error('Mission data is unavailable or invalid.');
        setMissionCard(normalizedCard);
        setMission((prev) => ({ ...prev, id: normalizedCard.missionId, uavId: normalizedCard.uavId, card: normalizedCard }));
        setPriorityZones(normalizedCard.priorityZones);
        setWaypoints(normalizedCard.waypoints ?? []);
        setMissionSource('LIVE');
        setErrors((prev) => ({ ...prev, missionError: null }));
      } catch (error) {
        if (cancelled) return;
        const message = error instanceof ApiRequestError ? error.message : 'Mission data is unavailable or invalid.';
        setMissionLoading(false);
        setMissionSource('UNAVAILABLE');
        setPriorityZones([]);
        setErrors((prev) => ({ ...prev, missionError: message }));
      }
      setMissionLoading(false);
    };

    const loadGovernor = async () => {
      const governorData = await fetchGovernorState();
      if (cancelled) return;
      if (governorData) {
        setGovernor({
          decision: governorData.decision === 'SUPPRESS' || governorData.decision === 'RETAIN' || governorData.decision === 'EVENT' || governorData.decision === 'EVIDENCE' ? governorData.decision : 'UNKNOWN',
          reason: typeof governorData.reason === 'string' ? governorData.reason : 'Governed by backend state.',
          action: typeof governorData.action === 'string' ? governorData.action : 'No live decision available.',
          evaluatedConditions: {
            communicationAvailable: Boolean(governorData.evaluated_conditions?.communicationAvailable),
            batteryAboveThreshold: Boolean(governorData.evaluated_conditions?.batteryAboveThreshold),
            relevantObject: Boolean(governorData.evaluated_conditions?.relevantObject),
            insidePriorityZone: Boolean(governorData.evaluated_conditions?.insidePriorityZone),
            persistenceSatisfied: Boolean(governorData.evaluated_conditions?.persistenceSatisfied),
            evidenceRequired: Boolean(governorData.evaluated_conditions?.evidenceRequired)
          },
          timestamp: typeof governorData.timestamp === 'string' ? governorData.timestamp : 'NO DATA',
          targetType: typeof governorData.target_type === 'string' && isObjectClass(governorData.target_type) ? governorData.target_type : undefined,
          zoneName: typeof governorData.zone_name === 'string' ? governorData.zone_name : undefined,
          confidence: typeof governorData.confidence === 'number' ? governorData.confidence : undefined
        });
        setErrors((prev) => ({ ...prev, governorError: null }));
      } else {
        setErrors((prev) => ({ ...prev, governorError: 'Governor data is unavailable.' }));
      }
    };

    const loadCommunication = async () => {
      const commData = await fetchCommunicationStatus();
      if (cancelled) return;
      if (commData) {
        const linkAvailable = Boolean(commData.link_available ?? commData.state === 'ACTIVE');
        setCommunication({
          status: linkAvailable ? 'ACTIVE' : 'OFFLINE',
          packets: Number(commData.packets_transmitted ?? commData.packets_generated ?? 0),
          bytes: Number(commData.bytes_transmitted ?? commData.bytes_generated ?? 0),
          transmissionDurationSec: Number(commData.transmission_duration || 0),
          lastTransmission: commData.last_tx_timestamp ?? commData.lastTransmission ?? 'NO DATA',
          lastPacketType: commData.last_packet_type ?? 'NONE',
          channelFrequency: commData.channel ?? 'NO DATA',
          snr: Number(commData.snr ?? 0),
          dutyCyclePercent: Number(commData.duty_cycle_percent ?? 0),
          rfSilencePercent: Number(commData.rf_silence_percent ?? 0),
          linkAvailable
        });
        setErrors((prev) => ({ ...prev, communicationError: null }));
      } else {
        setErrors((prev) => ({ ...prev, communicationError: 'Communication data is unavailable.' }));
      }
    };

    const pollRuntime = async () => {
      const health = await checkBackendHealth();
      const online = health.status === 'ok' || health.status === 'OK';
      if (!online) {
        if (cancelled) return;
        setBackendConnected(false);
        setConnectionStatus('OFFLINE');
        setTelemetry({ ...UNKNOWN_TELEMETRY });
        setLiveDetections([]);
        setDetectorStatus(null);
        setCameraStatus(null);
        setGovernor({ ...UNKNOWN_GOVERNOR });
        setCommunication({ ...UNKNOWN_COMMUNICATION });
        setErrors((prev) => ({ ...prev, backendError: `Backend health: ${health.status}` }));
        return;
      }

      setBackendConnected(true);
      setErrors((prev) => ({ ...prev, backendError: null }));
      const status = await getRuntimeStatus();
      if (!cancelled) {
        if (status) hydrateTelemetryFromStatus(status);
        else {
          setErrors((prev) => ({ ...prev, telemetryError: 'Runtime status request failed.' }));
          hydrateTelemetryFromStatus(null);
        }
      }
      const commandLogData = await getFlightCommandLog();
      if (!cancelled) setCommandLog(commandLogData.entries);
      const [cardData, governorData, commData, liveCameraStatus, backendDetections, liveDetectorStatus] = await Promise.all([
        fetchMission(),
        fetchGovernorState(),
        fetchCommunicationStatus(),
        getCameraStatus(),
        fetchDetections(),
        getDetectorStatus()
      ]);
      if (!cancelled) {
        const normalizedCard = cardData && normalizeMissionCard(cardData);
        if (normalizedCard) {
          setMissionCard(normalizedCard);
          setMission((prev) => ({ ...prev, id: normalizedCard.missionId, uavId: normalizedCard.uavId, card: normalizedCard }));
          setPriorityZones(normalizedCard.priorityZones);
          setWaypoints(normalizedCard.waypoints ?? []);
          setMissionSource('LIVE');
          setMissionLoading(false);
        }
        if (governorData) {
          setGovernor({
            decision: governorData.decision === 'SUPPRESS' || governorData.decision === 'RETAIN' || governorData.decision === 'EVENT' || governorData.decision === 'EVIDENCE' ? governorData.decision : 'UNKNOWN',
            reason: typeof governorData.reason === 'string' ? governorData.reason : 'Governed by backend state.',
            action: typeof governorData.action === 'string' ? governorData.action : 'No live decision available.',
            evaluatedConditions: {
              communicationAvailable: Boolean(governorData.evaluated_conditions?.communicationAvailable),
              batteryAboveThreshold: Boolean(governorData.evaluated_conditions?.batteryAboveThreshold),
              relevantObject: Boolean(governorData.evaluated_conditions?.relevantObject),
              insidePriorityZone: Boolean(governorData.evaluated_conditions?.insidePriorityZone),
              persistenceSatisfied: Boolean(governorData.evaluated_conditions?.persistenceSatisfied),
              evidenceRequired: Boolean(governorData.evaluated_conditions?.evidenceRequired)
            },
            timestamp: typeof governorData.timestamp === 'string' ? governorData.timestamp : 'NO DATA',
            targetType: typeof governorData.target_type === 'string' && isObjectClass(governorData.target_type) ? governorData.target_type : undefined,
            zoneName: typeof governorData.zone_name === 'string' ? governorData.zone_name : undefined,
            confidence: typeof governorData.confidence === 'number' ? governorData.confidence : undefined
          });
        }
        if (commData) {
          const linkAvailable = Boolean(commData.link_available ?? commData.state === 'ACTIVE');
          setCommunication({
            status: commData.state === 'INACTIVE' ? 'INACTIVE' : linkAvailable ? 'ACTIVE' : 'OFFLINE',
            packets: Number(commData.packets_transmitted ?? commData.packets_generated ?? 0),
            bytes: Number(commData.bytes_transmitted ?? commData.bytes_generated ?? 0),
            transmissionDurationSec: Number(commData.transmission_duration || 0),
            lastTransmission: commData.last_tx_timestamp ?? commData.lastTransmission ?? 'NO DATA',
            lastPacketType: commData.last_packet_type ?? 'NONE',
            channelFrequency: commData.channel ?? 'NO DATA',
            snr: Number(commData.snr ?? 0),
            dutyCyclePercent: Number(commData.duty_cycle_percent ?? 0),
            rfSilencePercent: Number(commData.rf_silence_percent ?? 0),
            linkAvailable,
            suppressedEvents: Number(commData.suppressed ?? 0),
            retainedEvents: Number(commData.retained ?? 0),
            packetsTransmitted: Number(commData.packets_sent ?? 0),
            bytesTransmitted: Number(commData.bytes_transmitted ?? 0),
            eventsTransmitted: Number(commData.events_transmitted ?? 0),
            evidenceTransmitted: Number(commData.evidence_transmitted ?? 0)
          });
        }
        setLiveDetections(backendDetections.map(normalizeDetection));
        setDetectorStatus(liveDetectorStatus);
        setCameraStatus(liveCameraStatus);
      }
    };

    void pollRuntime();
    const interval = window.setInterval(() => void pollRuntime(), 1000);

    return () => {
      cancelled = true;
      window.clearInterval(interval);
    };
  }, [hydrateTelemetryFromStatus, normalizeDetection]);

  const handleConnectSimulator = useCallback(async (
    mode: 'local' | 'cloud' | 'fallback' = 'local',
    host?: string,
    port?: number,
    endpoint?: string
  ) => {
    setIsConnecting(true);
    try {
      const result = await apiConnectSimulator(mode, host, port, endpoint);
      setSimulatorMode(mode);
      return result;
    } finally {
      setIsConnecting(false);
    }
  }, []);

  const handleDisconnectSimulator = useCallback(async () => {
    const result = await apiDisconnectSimulator();
    setConnectionStatus('OFFLINE');
    setTelemetry({ ...UNKNOWN_TELEMETRY });
    return result;
  }, []);

  const saveMissionCard = useCallback(async (newCard: MissionCard) => {
    setMissionSaveState('SAVING');
    setMissionSaveError(null);

    try {
      await saveMission({
        ...newCard,
        waypoints: (newCard.waypoints ?? []).map(({ lng, acceptanceRadius, ...waypoint }) => ({
          ...waypoint,
          lon: lng,
          acceptanceRadius: acceptanceRadius ?? 10
        }))
      });
      const refreshedCard = await fetchMission();
      const normalizedCard = refreshedCard && normalizeMissionCard(refreshedCard);
      if (!normalizedCard) throw new Error('Mission save succeeded but the backend returned invalid mission data.');
      setMissionCard(normalizedCard);
      setMission((prev) => ({ ...prev, id: normalizedCard.missionId, uavId: normalizedCard.uavId, card: normalizedCard }));
      setPriorityZones(normalizedCard.priorityZones);
      setWaypoints(normalizedCard.waypoints ?? []);
      setMissionSource('LIVE');
      setMissionLoading(false);
      setMissionSaveError(null);
      setMissionSaveState('SAVED');
    } catch (error) {
      const message = error instanceof ApiRequestError ? error.message : 'Mission save failed.';
      setMissionSaveError(message);
      setMissionSaveState('SAVE_FAILED');
      throw new Error(message);
    }
  }, []);

  const value: SimulationContextValue = {
    mission,
    missionCard,
    telemetry,
    governor,
    communication,
    metrics,
    detections: liveDetections,
    timeline,
    evidence,
    waypoints,
    priorityZones,
    isRunning,
    connectionStatus,
    simulatorMode,
    lastTelemetryTimestamp,
    backendConnected,
    isConnecting,
    errors,
    missionLoading,
    missionSource,
    missionSaveState,
    missionSaveError,
    commandLog,
    detectorStatus,
    cameraStatus,
    connectSimulator: handleConnectSimulator,
    disconnectSimulator: handleDisconnectSimulator,
    arm: armDrone,
    disarm: disarmDrone,
    takeoff: takeoffDrone,
    land: landDrone,
    hover: hoverDrone,
    move: moveDrone,
    setHeading: setHeadingDrone,
    returnToHome: returnToHomeDrone,
    saveMissionCard,
    toggleSimulation: () => takeoffDrone(10),
    stepSimulation: () => moveDrone(2, 0, 0, 0),
    resetSimulation: returnToHomeDrone
  };

  return createElement(SimulationContext.Provider, { value }, children);
}

export function useSimulation(): SimulationContextValue {
  const context = useContext(SimulationContext);
  if (!context) throw new Error('useSimulation must be used within SimulationProvider');
  return context;
}
