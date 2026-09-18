import React from 'react';
import { useSimulation } from '../../hooks/useSimulation';
import { DecisionBadge } from './DecisionBadge';
import { DecisionReason } from './DecisionReason';
import { Shield, Radio, EyeOff, FolderArchive } from 'lucide-react';
import { GovernorState } from '../../types';

export const GovernorPanel: React.FC = () => {
  const { governor, detections } = useSimulation();

  const statesConfig: Array<{
    id: GovernorState;
    title: string;
    icon: React.ReactNode;
    color: string;
    border: string;
    activeBorder: string;
    activeBg: string;
    summary: string;
  }> = [
    {
      id: 'SUPPRESS',
      title: 'SUPPRESS',
      icon: <EyeOff className="w-5 h-5" />,
      color: 'text-slate-400',
      border: 'border-slate-800',
      activeBorder: 'border-slate-500 shadow-slate-900',
      activeBg: 'bg-slate-800/40',
      summary: 'Target is not mission relevant or lacks basic validity. Discarded at edge. Zero RF emissions.'
    },
    {
      id: 'RETAIN',
      title: 'RETAIN',
      icon: <FolderArchive className="w-5 h-5" />,
      color: 'text-amber-400',
      border: 'border-slate-800',
      activeBorder: 'border-amber-500/60 shadow-amber-950/40',
      activeBg: 'bg-amber-950/20',
      summary: 'Target is mission-relevant but outside priority zones or persistence threshold. Cached locally.'
    },
    {
      id: 'EVENT',
      title: 'EVENT',
      icon: <Radio className="w-5 h-5" />,
      color: 'text-cyan-400',
      border: 'border-slate-800',
      activeBorder: 'border-cyan-500/60 shadow-cyan-950/40',
      activeBg: 'bg-cyan-950/20',
      summary: 'Target satisfies priority zone and temporal persistence. Ultra-compact metadata packet emitted.'
    },
    {
      id: 'EVIDENCE',
      title: 'EVIDENCE',
      icon: <Shield className="w-5 h-5" />,
      color: 'text-purple-400',
      border: 'border-slate-800',
      activeBorder: 'border-purple-500/60 shadow-purple-950/40',
      activeBg: 'bg-purple-950/20',
      summary: 'High-value target requiring verification. Image clip or telemetry payload queued for transmission.'
    }
  ];

  return (
    <div className="space-y-6">
      {/* Philosophy Banner */}
      <div className="bg-gradient-to-r from-[#09111e] via-[#0e1726] to-[#09111e] border border-cyan-900/40 p-4 rounded-xl flex items-center justify-between">
        <div>
          <div className="text-[11px] font-mono text-cyan-400 uppercase tracking-widest font-semibold">
            S.I.G.H.T. Core Principle
          </div>
          <div className="text-base sm:text-lg font-bold text-slate-100 mt-0.5">
            "PERCEPTION ≠ COMMUNICATION DECISION"
          </div>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl font-sans">
            Edge AI detects everything in sight; Mission Context determines what is relevant; S.I.G.H.T. Governor decides what should be communicated; Communication Controller decides how/when to transmit.
          </p>
        </div>
        <div className="hidden md:flex flex-col items-end text-right font-mono">
          <span className="text-[10px] text-slate-400">GOVERNOR STATE MACHINE</span>
          <span className="text-xs text-emerald-400 font-bold">ONLINE & AUTONOMOUS</span>
        </div>
      </div>

      {/* Prominent Current Decision Hero */}
      <div className="bg-[#0b1019] rounded-xl p-6 border border-slate-800 shadow-2xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-5 border-b border-slate-800/80">
          <div>
            <span className="text-xs font-mono uppercase tracking-widest text-slate-400 block mb-1">
              Active Governor Decision
            </span>
            <div className="flex items-center gap-3">
              <DecisionBadge decision={governor.decision} size="xl" pulse={true} />
              {governor.targetType && (
                <span className="text-xs font-mono bg-slate-800/80 text-slate-300 px-2.5 py-1 rounded border border-slate-700">
                  Target: {governor.targetType} ({governor.targetId || 'DET-LIVE'})
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center gap-6 font-mono text-xs">
            <div>
              <span className="text-slate-400 block text-[10px] uppercase">Decision Timestamp</span>
              <span className="text-slate-200 font-semibold">{governor.timestamp}</span>
            </div>
            <div>
              <span className="text-slate-400 block text-[10px] uppercase">Decoupled Architecture</span>
              <span className="text-cyan-400 font-semibold">SIGHT-CORE v1.0</span>
            </div>
          </div>
        </div>

        {/* Reason and Evaluated Conditions */}
        <div className="mt-5">
          <DecisionReason governorDecision={governor} />
        </div>
      </div>

      {/* The 4 Architectural States */}
      <div>
        <div className="text-xs font-mono uppercase tracking-widest text-slate-400 font-bold mb-3">
          4 Governor Decision States
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
          {statesConfig.map((st) => {
            const isCurrent = governor.decision === st.id;
            return (
              <div
                key={st.id}
                className={`p-4 rounded-lg border transition-all duration-200 ${
                  isCurrent
                    ? `${st.activeBorder} ${st.activeBg} ring-1 ring-cyan-500/20`
                    : 'bg-[#0b1019]/60 border-slate-800/80'
                }`}
              >
                <div className="flex items-center justify-between mb-2">
                  <span className={`flex items-center gap-2 font-mono font-bold text-sm ${st.color}`}>
                    {st.icon}
                    {st.title}
                  </span>
                  {isCurrent && (
                    <span className="text-[9px] font-mono uppercase px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                      CURRENT
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-400 leading-relaxed font-sans mt-2">
                  {st.summary}
                </p>
              </div>
            );
          })}
        </div>
      </div>

      {/* Recent Evaluations Table */}
      <div className="bg-[#0b1019] rounded-xl p-5 border border-slate-800">
        <div className="flex items-center justify-between mb-3">
          <div className="text-xs font-mono uppercase tracking-widest text-slate-400 font-bold">
            Recent Detection Decisions Stream
          </div>
          <span className="text-xs font-mono text-slate-400">
            {detections.length} EVALUATED TARGETS
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 text-[11px]">
                <th className="pb-2">TIME</th>
                <th className="pb-2">TARGET</th>
                <th className="pb-2">CONFIDENCE</th>
                <th className="pb-2">ZONE LOCATION</th>
                <th className="pb-2">PERSISTENCE</th>
                <th className="pb-2 text-right">DECISION</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {detections.slice(0, 6).map((det) => (
                <tr key={det.id} className="hover:bg-slate-800/20 transition-colors">
                  <td className="py-2.5 text-slate-400">{det.timestamp}</td>
                  <td className="py-2.5 font-bold text-slate-200">{det.object}</td>
                  <td className="py-2.5 text-slate-300">{det.confidence}%</td>
                  <td className="py-2.5 text-slate-400 truncate max-w-xs">{det.locationName}</td>
                  <td className="py-2.5 text-slate-400">{det.persistence} frames</td>
                  <td className="py-2.5 text-right">
                    <DecisionBadge decision={det.governorDecision} size="sm" />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
