import React, { useState, useEffect } from 'react';
import { useSimulation } from '../../hooks/useSimulation';
import { StatusBadge } from '../common/StatusBadge';
import { checkBackendHealth } from '../../services/api';
import {
  Radio,
  Play,
  Pause,
  RotateCcw,
  SkipForward,
  Shield,
  Activity,
  BatteryCharging,
  Server
} from 'lucide-react';

export const TopBar: React.FC = () => {
  const {
    mission,
    telemetry,
    governor,
    communication,
    isRunning,
    toggleSimulation,
    stepSimulation,
    resetSimulation
  } = useSimulation();

  const [utcTime, setUtcTime] = useState<string>('');
  const [backendOnline, setBackendOnline] = useState<boolean>(false);

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setUtcTime(
        `${String(now.getUTCHours()).padStart(2, '0')}:${String(
          now.getUTCMinutes()
        ).padStart(2, '0')}:${String(now.getUTCSeconds()).padStart(2, '0')} UTC`
      );
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);

    const checkHealth = () => {
      checkBackendHealth().then(res => {
        setBackendOnline(res.status === 'OPERATIONAL');
      }).catch(() => setBackendOnline(false));
    };
    checkHealth();
    const healthInterval = setInterval(checkHealth, 5000);

    return () => {
      clearInterval(interval);
      clearInterval(healthInterval);
    };
  }, []);

  const getGovernorVariant = (decision: string) => {
    switch (decision) {
      case 'EVENT':
        return 'cyan';
      case 'RETAIN':
        return 'amber';
      case 'EVIDENCE':
        return 'violet';
      default:
        return 'slate';
    }
  };

  return (
    <header className="h-16 bg-[#090d15] border-b border-slate-800/80 px-4 flex items-center justify-between select-none z-30 shrink-0">
      {/* Brand & Mission Identification */}
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
            <Shield className="w-4 h-4" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-bold tracking-widest text-slate-100 font-mono text-sm">
                S.I.G.H.T.
              </span>
              <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700">
                GCS v1.0
              </span>
            </div>
            <div className="text-[10px] text-slate-400 font-mono hidden sm:block">
              SILENT INTELLIGENCE GATHERING & HIDDEN TRANSMISSION
            </div>
          </div>
        </div>

        <div className="h-8 w-px bg-slate-800/80 mx-1 hidden md:block" />

        {/* Mission Quick Callouts */}
        <div className="hidden lg:flex items-center gap-4 text-xs font-mono">
          <div>
            <span className="text-slate-400 block text-[10px] uppercase">Mission</span>
            <span className="text-cyan-400 font-bold">{mission.id}</span>
          </div>
          <div>
            <span className="text-slate-400 block text-[10px] uppercase">UAV Platform</span>
            <span className="text-slate-200 font-semibold">{mission.uavId}</span>
          </div>
        </div>
      </div>

      {/* Operational Status Badges */}
      <div className="flex items-center gap-3">
        {/* Telemetry quick status */}
        <div className="hidden md:flex items-center gap-3 text-xs font-mono bg-[#0c121d] px-3 py-1.5 rounded border border-slate-800">
          <div className="flex items-center gap-1.5" title="FastAPI S.I.G.H.T. Core Backend">
            <Server className={`w-3.5 h-3.5 ${backendOnline ? 'text-emerald-400' : 'text-red-400'}`} />
            <span className="text-slate-400">BACKEND:</span>
            <span className={`font-bold ${backendOnline ? 'text-emerald-400' : 'text-red-400'}`}>
              {backendOnline ? 'CONNECTED' : 'OFFLINE'}
            </span>
          </div>

          <div className="w-px h-3.5 bg-slate-700" />

          <div className="flex items-center gap-1.5">
            <Activity className="w-3.5 h-3.5 text-emerald-400" />
            <span className="text-slate-400">SYS:</span>
            <span className="text-emerald-400 font-bold">ONLINE</span>
          </div>

          <div className="w-px h-3.5 bg-slate-700" />

          <div className="flex items-center gap-1.5">
            <BatteryCharging className="w-3.5 h-3.5 text-amber-400" />
            <span className="text-slate-400">BATT:</span>
            <span className={`font-bold ${telemetry.battery < 25 ? 'text-red-400' : 'text-amber-400'}`}>
              {telemetry.battery}%
            </span>
          </div>

          <div className="w-px h-3.5 bg-slate-700" />

          <div className="flex items-center gap-1.5">
            <span className="text-slate-400">GPS:</span>
            <span className="text-emerald-400 font-bold">{telemetry.gpsStatus}</span>
          </div>

          <div className="w-px h-3.5 bg-slate-700" />

          <div className="flex items-center gap-1.5">
            <Radio className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-400">RF LINK:</span>
            <span
              className={`font-bold ${
                communication.status === 'ACTIVE'
                  ? 'text-cyan-400 animate-pulse'
                  : 'text-slate-400'
              }`}
            >
              {communication.status}
            </span>
          </div>
        </div>

        {/* Current Governor Decision Chip */}
        <div className="flex items-center gap-2 bg-[#0c121d] px-2.5 py-1 rounded border border-slate-800">
          <span className="text-[10px] text-slate-400 font-mono uppercase hidden sm:inline">
            GOVERNOR:
          </span>
          <StatusBadge
            label={governor.decision}
            variant={getGovernorVariant(governor.decision)}
            pulse={governor.decision === 'EVENT' || governor.decision === 'EVIDENCE'}
            size="sm"
          />
        </div>

        {/* Simulation Controls */}
        <div className="flex items-center gap-1 bg-[#0c121d] p-1 rounded border border-slate-800">
          <button
            onClick={toggleSimulation}
            title={isRunning ? 'Pause Simulation' : 'Run Simulation'}
            className={`p-1.5 rounded transition-colors ${
              isRunning
                ? 'bg-amber-500/20 text-amber-400 hover:bg-amber-500/30'
                : 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30'
            }`}
          >
            {isRunning ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
          </button>
          <button
            onClick={stepSimulation}
            title="Step Simulation Forward"
            className="p-1.5 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          >
            <SkipForward className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={resetSimulation}
            title="Reset Simulation State"
            className="p-1.5 rounded text-slate-400 hover:text-slate-200 hover:bg-slate-800 transition-colors"
          >
            <RotateCcw className="w-3.5 h-3.5" />
          </button>
        </div>

        {/* UTC Clock */}
        <div className="hidden xl:block font-mono text-xs text-cyan-400 font-semibold px-2 py-1 bg-cyan-950/30 border border-cyan-800/40 rounded">
          {utcTime}
        </div>
      </div>
    </header>
  );
};
