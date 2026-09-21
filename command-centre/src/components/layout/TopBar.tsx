import React from 'react';
import { useSimulation } from '../../hooks/useSimulation';
import {
  Shield,
  Radio,
  BatteryCharging
} from 'lucide-react';

export const TopBar: React.FC = () => {
  const {
    mission,
    telemetry,
    connectionStatus,
    backendConnected
  } = useSimulation();

  return (
    <header className="min-h-16 bg-[#090d15] border-b border-slate-800/80 px-4 py-2 flex items-center select-none z-30 shrink-0">
      <div className="flex min-w-0 w-full items-center gap-3 lg:gap-5">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
            <Shield className="w-4 h-4" />
          </div>
          <div>
            <span className="font-bold tracking-widest text-slate-100 font-mono text-sm">S.I.G.H.T.</span>
          </div>
        </div>

        <div className="h-8 w-px bg-slate-800/80 hidden sm:block" />

        <div className="min-w-0 flex-1 hidden sm:flex items-center gap-4 font-mono">
          <div className="min-w-0">
            <span className="text-[10px] text-slate-500 uppercase block">Mission</span>
            <span className="text-cyan-400 font-bold truncate block">{mission.id}</span>
          </div>
          <div className="min-w-0 hidden md:block">
            <span className="text-[10px] text-slate-500 uppercase block">Objective</span>
            <span className="text-slate-200 font-semibold truncate block">{mission.card.objective}</span>
          </div>
          <span className="text-slate-300 font-semibold whitespace-nowrap">{mission.uavId}</span>
        </div>

        <div className="flex items-center gap-2 sm:gap-3 text-xs font-mono shrink-0">
          <div className="flex items-center gap-1.5" title="Backend and telemetry status">
            <span className={`h-2 w-2 rounded-full ${connectionStatus === 'LIVE' ? 'bg-emerald-400 animate-pulse' : connectionStatus === 'STALE' ? 'bg-amber-400' : 'bg-slate-500'}`} />
            <span className={connectionStatus === 'LIVE' ? 'text-emerald-400' : connectionStatus === 'STALE' ? 'text-amber-400' : 'text-slate-400'}>
              {connectionStatus}
            </span>
          </div>
          <div className="hidden md:flex items-center gap-1.5 text-slate-400">
            <Radio className={`w-3.5 h-3.5 ${backendConnected ? 'text-cyan-400' : 'text-slate-500'}`} />
            <span>{backendConnected ? 'LINK ACTIVE' : 'LINK OFFLINE'}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <BatteryCharging className="w-3.5 h-3.5 text-amber-400" />
            <span className="text-amber-400 font-bold">{telemetry.hasTelemetry ? `${telemetry.battery}%` : 'N/A'}</span>
          </div>
        </div>
      </div>
    </header>
  );
};
