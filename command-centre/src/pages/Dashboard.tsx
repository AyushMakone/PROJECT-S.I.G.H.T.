import React from 'react';
import { useSimulation } from '../hooks/useSimulation';
import { MissionMap } from '../components/map/MissionMap';
import { MissionSummary } from '../components/dashboard/MissionSummary';
import { UAVStatus } from '../components/dashboard/UAVStatus';
import { GovernorStatus } from '../components/dashboard/GovernorStatus';
import { LatestEventCard } from '../components/dashboard/LatestEventCard';
import { DashboardMetrics } from '../components/dashboard/DashboardMetrics';
import { Timeline } from '../components/common/Timeline';
import { Clock } from 'lucide-react';

export const Dashboard: React.FC = () => {
  const { telemetry, waypoints, priorityZones, detections, timeline } = useSimulation();

  return (
    <div className="p-4 space-y-4 max-w-[1700px] mx-auto w-full">
      {/* Top Row: Mission Summary & UAV Avionics Bar */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <MissionSummary />
        <UAVStatus />
      </div>

      {/* Main Center Area: Large Tactical Map + Side Status Columns */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Large Tactical Map (8 cols) */}
        <div className="lg:col-span-8 flex flex-col">
          <div className="h-[480px] w-full rounded-xl overflow-hidden shadow-2xl">
            <MissionMap
              telemetry={telemetry}
              waypoints={waypoints}
              priorityZones={priorityZones}
              detections={detections}
              height="480px"
              enableMissionEditing={false}
            />
          </div>

          {/* Dynamic Metrics Row beneath map */}
          <div className="mt-4">
            <DashboardMetrics />
          </div>
        </div>

        {/* Right Tactical Column (4 cols) */}
        <div className="lg:col-span-4 flex flex-col gap-4">
          {/* Current Governor Decision */}
          <GovernorStatus />

          {/* Latest AI Event */}
          <LatestEventCard />

          {/* Mission Event Timeline */}
          <div className="bg-[#0b1019] rounded-xl p-4 border border-slate-800 font-mono flex-1 flex flex-col min-h-[220px]">
            <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4 text-cyan-400" />
                <span className="text-xs text-slate-300 font-bold uppercase tracking-wider">
                  MISSION TIMELINE
                </span>
              </div>
              <span className="text-[10px] text-slate-400">REAL-TIME LOG</span>
            </div>

            <div className="flex-1 overflow-hidden">
              <Timeline events={timeline} maxItems={6} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
