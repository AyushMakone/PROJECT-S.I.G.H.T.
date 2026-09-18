import React from 'react';
import { useSimulation } from '../hooks/useSimulation';
import { MissionMap } from '../components/map/MissionMap';
import { Navigation } from 'lucide-react';

export const MapView: React.FC = () => {
  const { telemetry, waypoints, priorityZones, detections, mission } = useSimulation();

  return (
    <div className="flex-1 flex flex-col h-full p-4 space-y-3">
      {/* Top Banner */}
      <div className="bg-[#0b1019] rounded-xl p-3.5 border border-slate-800 flex items-center justify-between font-mono text-xs">
        <div className="flex items-center gap-3">
          <Navigation className="w-4 h-4 text-cyan-400" />
          <span className="font-bold text-slate-100">FULL OPERATIONAL TACTICAL MAP</span>
          <span className="text-slate-400">|</span>
          <span className="text-cyan-400">MISSION: {mission.id}</span>
        </div>
        <div className="flex items-center gap-4 text-slate-300">
          <span>WAYPOINTS: <strong className="text-slate-100">{waypoints.length}</strong></span>
          <span>PRIORITY ZONES: <strong className="text-red-400">{priorityZones.length}</strong></span>
          <span>ACTIVE DETECTIONS: <strong className="text-cyan-400">{detections.length}</strong></span>
        </div>
      </div>

      {/* Expanded Map */}
      <div className="flex-1 min-h-[600px] w-full rounded-xl overflow-hidden shadow-2xl">
        <MissionMap
          telemetry={telemetry}
          waypoints={waypoints}
          priorityZones={priorityZones}
          detections={detections}
          height="100%"
        />
      </div>
    </div>
  );
};
