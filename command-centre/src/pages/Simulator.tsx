import React from 'react';
import { useSimulation } from '../hooks/useSimulation';
import { StatusBadge } from '../components/common/StatusBadge';
import { Cpu, Radio, Wind, Play, Pause, AlertCircle, Layers } from 'lucide-react';

export const Simulator: React.FC = () => {
  const { isRunning, toggleSimulation, stepSimulation, resetSimulation } = useSimulation();

  return (
    <div className="p-6 max-w-[1500px] mx-auto w-full space-y-6 font-mono">
      {/* Header */}
      <div className="bg-[#0b1019] rounded-xl p-6 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs text-cyan-400 uppercase tracking-widest font-semibold mb-1">
            <Cpu className="w-4 h-4" />
            <span>SITL Flight & Physics Simulation Interface</span>
          </div>
          <h2 className="text-2xl font-bold text-slate-100 tracking-tight">
            PX4 AUTOPILOT & GAZEBO SITL SIMULATOR
          </h2>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl font-sans">
            Coordinates software-in-the-loop simulation runs for synthetic multi-rotor and fixed-wing UAV mission testing.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <StatusBadge
            label={isRunning ? 'SIM RUNNING' : 'SIM PAUSED'}
            variant={isRunning ? 'emerald' : 'amber'}
            pulse={isRunning}
            size="md"
          />
        </div>
      </div>

      {/* Simulator Connections Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-[#0b1019] rounded-xl p-5 border border-slate-800 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 uppercase font-bold flex items-center gap-2">
              <Radio className="w-4 h-4 text-cyan-400" />
              PX4 Autopilot SITL
            </span>
            <span className="text-[10px] text-emerald-400 bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-800/40">
              STANDBY
            </span>
          </div>
          <div className="space-y-1.5 text-xs">
            <div className="flex justify-between text-slate-400">
              <span>MAVLink Bridge:</span>
              <span className="text-slate-200">udp://127.0.0.1:14550</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Firmware Version:</span>
              <span className="text-slate-200">PX4 Autopilot v1.14.2</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Airframe Profile:</span>
              <span className="text-cyan-400 font-bold">Standard Quadrotor x500</span>
            </div>
          </div>
        </div>

        <div className="bg-[#0b1019] rounded-xl p-5 border border-slate-800 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 uppercase font-bold flex items-center gap-2">
              <Layers className="w-4 h-4 text-purple-400" />
              Gazebo Synthetic World
            </span>
            <span className="text-[10px] text-emerald-400 bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-800/40">
              READY
            </span>
          </div>
          <div className="space-y-1.5 text-xs">
            <div className="flex justify-between text-slate-400">
              <span>World Model:</span>
              <span className="text-slate-200">proving_ground_sector4.sdf</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Sensor Rig:</span>
              <span className="text-slate-200">Gimbal 4K EO / Thermal FLIR</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Physics Step:</span>
              <span className="text-cyan-400 font-bold">250 Hz Real-Time</span>
            </div>
          </div>
        </div>

        <div className="bg-[#0b1019] rounded-xl p-5 border border-slate-800 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-400 uppercase font-bold flex items-center gap-2">
              <Wind className="w-4 h-4 text-amber-400" />
              Environment & Wind
            </span>
            <span className="text-[10px] text-cyan-400 bg-cyan-950/40 px-2 py-0.5 rounded border border-cyan-800/40">
              ACTIVE
            </span>
          </div>
          <div className="space-y-1.5 text-xs">
            <div className="flex justify-between text-slate-400">
              <span>Base Wind:</span>
              <span className="text-slate-200">2.4 m/s (Bearing 220°)</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Gust Factor:</span>
              <span className="text-slate-200">Light turbulence (0.4 m/s)</span>
            </div>
            <div className="flex justify-between text-slate-400">
              <span>Sun Azimuth:</span>
              <span className="text-amber-400 font-bold">142° (Solar Noon)</span>
            </div>
          </div>
        </div>
      </div>

      {/* Manual Mock Simulation Triggers */}
      <div className="bg-[#0b1019] rounded-xl p-5 border border-slate-800 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <span className="text-xs text-slate-400 uppercase tracking-wider font-bold">
            Interactive Command Centre Simulation Runner
          </span>
          <span className="text-[10px] text-slate-400">OPERATOR OVERRIDE</span>
        </div>

        <p className="text-xs text-slate-400 font-sans leading-relaxed">
          The embedded simulation engine reproduces realistic UAV flight dynamics along waypoints, simulates periodic AI target detections in priority zones, evaluates S.I.G.H.T. Governor decisions, and calculates dynamic communication reduction metrics.
        </p>

        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={toggleSimulation}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-bold text-xs transition-colors ${
              isRunning
                ? 'bg-amber-500/20 text-amber-400 hover:bg-amber-500/30 border border-amber-500/40'
                : 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 border border-emerald-500/40'
            }`}
          >
            {isRunning ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
            {isRunning ? 'Pause Real-Time Simulation' : 'Resume Simulation'}
          </button>

          <button
            onClick={stepSimulation}
            className="px-4 py-2 rounded-lg bg-slate-800 text-slate-200 hover:bg-slate-700 text-xs border border-slate-700 transition-colors"
          >
            Step 1 Frame (1.5s)
          </button>

          <button
            onClick={resetSimulation}
            className="px-4 py-2 rounded-lg bg-slate-800 text-slate-200 hover:bg-slate-700 text-xs border border-slate-700 transition-colors"
          >
            Reset Flight to Initial State
          </button>
        </div>
      </div>

      {/* Modular Notice */}
      <div className="flex items-start gap-2 p-4 rounded-xl bg-slate-900/70 border border-slate-800 text-xs text-slate-400 font-sans">
        <AlertCircle className="w-4 h-4 text-cyan-400 shrink-0 mt-0.5" />
        <div>
          <strong className="text-slate-200">Decoupled Simulator Roadmap: </strong>
          Hardware-in-the-loop PX4 and Gazebo binaries reside in <code className="text-cyan-300">simulator/</code>. Later, the FastAPI backend will bridge MAVLink telemetry and YOLO camera streams directly to this page without frontend modifications.
        </div>
      </div>
    </div>
  );
};
