import React from 'react';
import { useSimulation } from '../../hooks/useSimulation';
import { StatusBadge } from '../common/StatusBadge';
import { Shield, Crosshair, Clock } from 'lucide-react';

export const MissionSummary: React.FC = () => {
  const { mission } = useSimulation();
  const card = mission.card;

  return (
    <div className="bg-[#0b1019] rounded-xl p-4 border border-slate-800 font-mono">
      <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <Shield className="w-4 h-4 text-cyan-400" />
          <span className="text-xs text-slate-300 font-bold uppercase tracking-wider">
            MISSION OVERVIEW
          </span>
        </div>
        <StatusBadge label={mission.status} variant="emerald" size="sm" pulse={true} />
      </div>

      <div className="grid grid-cols-2 gap-3 text-xs">
        <div>
          <span className="text-[10px] text-slate-400 block uppercase">Mission ID</span>
          <span className="font-bold text-cyan-400 text-sm">{card.missionId}</span>
        </div>

        <div>
          <span className="text-[10px] text-slate-400 block uppercase">UAV Callsign</span>
          <span className="font-bold text-slate-200 text-sm">{card.uavId}</span>
        </div>

        <div className="col-span-2">
          <span className="text-[10px] text-slate-400 block uppercase">Objective</span>
          <span className="font-semibold text-slate-100 flex items-center gap-1.5 mt-0.5">
            <Crosshair className="w-3.5 h-3.5 text-amber-400" />
            {card.objective}
          </span>
        </div>

        <div>
          <span className="text-[10px] text-slate-400 block uppercase">Relevant Objects</span>
          <span className="text-slate-300 truncate block mt-0.5 font-sans text-xs">
            {card.relevantObjects.join(', ')}
          </span>
        </div>

        <div>
          <span className="text-[10px] text-slate-400 block uppercase">Policy</span>
          <span className="text-emerald-400 font-bold block mt-0.5 text-xs">
            {card.communicationPolicy}
          </span>
        </div>
      </div>
    </div>
  );
};
