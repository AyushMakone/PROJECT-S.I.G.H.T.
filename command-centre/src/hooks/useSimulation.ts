import { useState, useEffect, useCallback } from 'react';
import { missionWs, ConnectionState } from '../services/websocket';
import {
  getFlightStatus,
  connectSimulator,
  disconnectSimulator,
  armDrone,
  disarmDrone,
  takeoffDrone,
  landDrone,
  hoverDrone,
  moveDrone,
  setHeadingDrone,
  returnToHomeDrone,
  fetchMission
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
  PriorityZone
} from '../types';
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
} from '../mock/missionData';

export function useSimulation() {
  // Primary operational state
  const [mission, setMission] = useState<Mission>({ ...INITIAL_MISSION });
  const [missionCard, setMissionCard] = useState<MissionCard>({ ...INITIAL_MISSION_CARD });
  const [telemetry, setTelemetry] = useState<Telemetry>({ ...INITIAL_TELEMETRY });
  const [governor, setGovernor] = useState<GovernorDecision>({ ...INITIAL_GOVERNOR_DECISION });
  const [communication, setCommunication] = useState<CommunicationStatus>({ ...INITIAL_COMMUNICATION_STATUS });
  const [metrics, setMetrics] = useState<MetricSummary>({ ...INITIAL_METRICS });
  const [detections, setDetections] = useState<Detection[]>([...INITIAL_DETECTIONS]);
  const [timeline, setTimeline] = useState<TimelineEvent[]>([...INITIAL_TIMELINE]);
  const [evidence, setEvidence] = useState<EvidenceItem[]>([...INITIAL_EVIDENCE]);
  const [waypoints] = useState<Waypoint[]>([...INITIAL_WAYPOINTS]);
  const [priorityZones] = useState<PriorityZone[]>([...INITIAL_PRIORITY_ZONES]);

  // Connection and simulator mode state
  const [connectionStatus, setConnectionStatus] = useState<ConnectionState>('SIMULATOR OFFLINE');
  const [simulatorMode, setSimulatorMode] = useState<'local' | 'cloud' | 'fallback'>('local');
  const [lastTelemetryTimestamp, setLastTelemetryTimestamp] = useState<string>('');
  const [isRunning, setIsRunning] = useState<boolean>(false);

  // Initialize WebSocket and real-time event listeners
  useEffect(() => {
    // 1. Connect WebSocket
    missionWs.connect();

    // 2. Track connection state
    const unsubStatus = missionWs.onStatusChange((status) => {
      setConnectionStatus(status);
      setIsRunning(status === 'TELEMETRY ACTIVE' || status === 'CONNECTED');
    });

    // 3. Ingest live genuine telemetry from backend WebSocket
    const unsubTelem = missionWs.on('telemetry', (data: any) => {
      if (!data) return;
      setTelemetry((prev) => ({
        ...prev,
        lat: typeof data.lat === 'number' ? data.lat : prev.lat,
        lng: typeof data.lng === 'number' ? data.lng : prev.lng,
        altitude: typeof data.altitude === 'number' ? data.altitude : prev.altitude,
        speed: typeof data.speed === 'number' ? data.speed : prev.speed,
        heading: data.heading || prev.heading,
        headingDegrees: typeof data.headingDegrees === 'number' ? data.headingDegrees : prev.headingDegrees,
        battery: typeof data.battery === 'number' ? data.battery : prev.battery,
        batteryVoltage: typeof data.batteryVoltage === 'number' ? data.batteryVoltage : prev.batteryVoltage,
        flightMode: data.flightMode || prev.flightMode,
        linkStatus: data.linkStatus || prev.linkStatus,
        systemStatus: data.systemStatus || prev.systemStatus,
        gpsStatus: data.gpsStatus || prev.gpsStatus,
        gpsSatellites: typeof data.gpsSatellites === 'number' ? data.gpsSatellites : prev.gpsSatellites,
        pitch: typeof data.pitch === 'number' ? data.pitch : prev.pitch,
        roll: typeof data.roll === 'number' ? data.roll : prev.roll,
        yaw: typeof data.yaw === 'number' ? data.yaw : prev.yaw,
        climbRate: typeof data.climbRate === 'number' ? data.climbRate : prev.climbRate,
        isArmed: typeof data.isArmed === 'boolean' ? data.isArmed : prev.isArmed
      }));

      if (data.timestamp) {
        setLastTelemetryTimestamp(data.timestamp);
      }
    });

    // 4. Ingest Governor decisions
    const unsubGov = missionWs.on('governor', (data: any) => {
      if (!data) return;
      setGovernor((prev) => ({
        ...prev,
        decision: data.decision || prev.decision,
        reason: data.reason || prev.reason,
        action: data.action || prev.action,
        timestamp: data.timestamp || prev.timestamp,
        targetType: data.target_type || prev.targetType,
        zoneName: data.zone_name || prev.zoneName
      }));

      // Append real timeline event
      const eventTitle = `Governor Decision: ${data.decision} (${data.target_type || 'Target'})`;
      setTimeline((prev) => [
        {
          id: `tl-gov-${Date.now()}`,
          timestamp: data.timestamp || new Date().toISOString(),
          category: 'GOVERNOR',
          title: eventTitle,
          detail: data.reason,
          level: data.decision === 'EVENT' ? 'success' : data.decision === 'RETAIN' ? 'warning' : 'info'
        },
        ...prev.slice(0, 49)
      ]);
    });

    // 5. Ingest Communication Controller status
    const unsubComm = missionWs.on('comm', (data: any) => {
      if (!data) return;
      setCommunication((prev) => ({
        ...prev,
        status: data.state || prev.status,
        packetsTransmitted: typeof data.packets_sent === 'number' ? data.packets_sent : prev.packetsTransmitted,
        bytesTransmitted: typeof data.bytes_transmitted === 'number' ? data.bytes_transmitted : prev.bytesTransmitted,
        eventsTransmitted: typeof data.events_transmitted === 'number' ? data.events_transmitted : prev.eventsTransmitted,
        evidenceTransmitted: typeof data.evidence_transmitted === 'number' ? data.evidence_transmitted : prev.evidenceTransmitted,
        suppressedEvents: typeof data.suppressed === 'number' ? data.suppressed : prev.suppressedEvents,
        retainedEvents: typeof data.retained === 'number' ? data.retained : prev.retainedEvents,
        linkAvailable: typeof data.link_available === 'boolean' ? data.link_available : prev.linkAvailable
      }));
    });

    // 6. Ingest status / mode changes
    const unsubMode = missionWs.on('status', (data: any) => {
      if (data.mode) {
        setSimulatorMode(data.mode);
      }
    });

    // Fetch initial mission card from backend
    fetchMission().then((cardData) => {
      if (cardData && cardData.missionId) {
        setMissionCard(cardData as any);
        setMission((prev) => ({ ...prev, id: cardData.missionId, card: cardData as any }));
      }
    }).catch(() => {});

    // Poll backend flight status on startup
    getFlightStatus().then((status) => {
      if (status) {
        setSimulatorMode(status.mode as any);
      }
    }).catch(() => {});

    return () => {
      unsubStatus();
      unsubTelem();
      unsubGov();
      unsubComm();
      unsubMode();
    };
  }, []);

  // Real Flight Control Actions
  const handleConnectSimulator = useCallback(async (mode: 'local' | 'cloud' | 'fallback' = 'local', host?: string, port?: number) => {
    setConnectionStatus('CONNECTING');
    const res = await connectSimulator(mode, host, port);
    setSimulatorMode(mode);
    setConnectionStatus(res.isConnected ? 'CONNECTED' : 'SIMULATOR OFFLINE');
    return res;
  }, []);

  const handleDisconnectSimulator = useCallback(async () => {
    await disconnectSimulator();
    setConnectionStatus('SIMULATOR OFFLINE');
  }, []);

  const handleArm = useCallback(async () => {
    return await armDrone();
  }, []);

  const handleDisarm = useCallback(async () => {
    return await disarmDrone();
  }, []);

  const handleTakeoff = useCallback(async (altitude: number = 10.0) => {
    return await takeoffDrone(altitude);
  }, []);

  const handleLand = useCallback(async () => {
    return await landDrone();
  }, []);

  const handleHover = useCallback(async () => {
    return await hoverDrone();
  }, []);

  const handleMove = useCallback(async (vx: number, vy: number, vz: number, yawRate: number = 0) => {
    return await moveDrone(vx, vy, vz, yawRate);
  }, []);

  const handleSetHeading = useCallback(async (heading: number) => {
    return await setHeadingDrone(heading);
  }, []);

  const handleRth = useCallback(async () => {
    return await returnToHomeDrone();
  }, []);

  const updateMissionCard = useCallback((newCard: MissionCard) => {
    setMissionCard(newCard);
    setMission((prev) => ({ ...prev, id: newCard.missionId, card: newCard }));
  }, []);

  return {
    mission,
    missionCard,
    telemetry,
    governor,
    communication,
    metrics,
    detections,
    timeline,
    evidence,
    waypoints,
    priorityZones,
    isRunning,
    connectionStatus,
    simulatorMode,
    lastTelemetryTimestamp,

    // Real Flight Control API commands
    connectSimulator: handleConnectSimulator,
    disconnectSimulator: handleDisconnectSimulator,
    arm: handleArm,
    disarm: handleDisarm,
    takeoff: handleTakeoff,
    land: handleLand,
    hover: handleHover,
    move: handleMove,
    setHeading: handleSetHeading,
    returnToHome: handleRth,
    updateMissionCard,

    // Backward-compatible triggers
    toggleSimulation: () => (isRunning ? handleLand() : handleTakeoff(10)),
    stepSimulation: () => handleMove(2, 0, 0, 0),
    resetSimulation: handleRth
  };
}
