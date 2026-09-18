import { useState, useEffect } from 'react';
import { simulationEngine } from '../services/mock/simulationEngine';
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

export function useSimulation() {
  const [mission, setMission] = useState<Mission>(simulationEngine.getMission());
  const [telemetry, setTelemetry] = useState<Telemetry>(simulationEngine.getTelemetry());
  const [governor, setGovernor] = useState<GovernorDecision>(simulationEngine.getGovernorDecision());
  const [communication, setCommunication] = useState<CommunicationStatus>(simulationEngine.getCommunicationStatus());
  const [metrics, setMetrics] = useState<MetricSummary>(simulationEngine.getMetrics());
  const [detections, setDetections] = useState<Detection[]>(simulationEngine.getDetections());
  const [timeline, setTimeline] = useState<TimelineEvent[]>(simulationEngine.getTimeline());
  const [evidence, setEvidence] = useState<EvidenceItem[]>(simulationEngine.getEvidence());
  const [isRunning, setIsRunning] = useState<boolean>(simulationEngine.getIsRunning());
  const [waypoints] = useState<Waypoint[]>(simulationEngine.getWaypoints());
  const [priorityZones] = useState<PriorityZone[]>(simulationEngine.getPriorityZones());

  useEffect(() => {
    const unsubMission = simulationEngine.onMission(setMission);
    const unsubTelemetry = simulationEngine.onTelemetry(setTelemetry);
    const unsubGovernor = simulationEngine.onGovernor(setGovernor);
    const unsubComm = simulationEngine.onCommunication(setCommunication);
    const unsubMetrics = simulationEngine.onMetrics(setMetrics);
    const unsubDetections = simulationEngine.onDetections(setDetections);
    const unsubTimeline = simulationEngine.onTimeline(setTimeline);
    const unsubEvidence = simulationEngine.onEvidence(setEvidence);
    const unsubRunning = simulationEngine.onRunningChange(setIsRunning);

    return () => {
      unsubMission();
      unsubTelemetry();
      unsubGovernor();
      unsubComm();
      unsubMetrics();
      unsubDetections();
      unsubTimeline();
      unsubEvidence();
      unsubRunning();
    };
  }, []);

  const toggleSimulation = () => simulationEngine.toggle();
  const stepSimulation = () => simulationEngine.step();
  const resetSimulation = () => simulationEngine.reset();
  const updateMissionCard = (card: MissionCard) => simulationEngine.updateMissionCard(card);

  return {
    mission,
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
    toggleSimulation,
    stepSimulation,
    resetSimulation,
    updateMissionCard
  };
}
