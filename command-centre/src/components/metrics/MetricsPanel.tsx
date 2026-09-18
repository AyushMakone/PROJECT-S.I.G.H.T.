import React from 'react';
import { useSimulation } from '../../hooks/useSimulation';
import { TrendingDown, Radio, Activity, HardDrive, Zap, Info } from 'lucide-react';

export const MetricsPanel: React.FC = () => {
  const { metrics } = useSimulation();

  // Dynamic formula calculation: ((Baseline - SIGHT) / Baseline) * 100
  const calcReduction = (baseline: number, sight: number): number => {
    if (baseline <= 0) return 0;
    const reduction = ((baseline - sight) / baseline) * 100;
    return Math.max(0, Math.min(100, Number(reduction.toFixed(1))));
  };

  const bytesReduction = calcReduction(metrics.baselineBytes, metrics.sightBytes);
  const packetsReduction = calcReduction(metrics.baselinePackets, metrics.sightPackets);
  const durationReduction = calcReduction(metrics.baselineDurationSec, metrics.sightDurationSec);

  const formatBytes = (bytes: number): string => {
    if (bytes >= 1048576) return `${(bytes / 1048576).toFixed(2)} MB`;
    if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${bytes} B`;
  };

  const formatDuration = (sec: number): string => {
    const mins = Math.floor(sec / 60);
    const remainingSec = sec % 60;
    if (mins > 0) return `${mins}m ${remainingSec}s`;
    return `${remainingSec}s`;
  };

  return (
    <div className="space-y-6 font-mono">
      {/* Reduction Hero Summary */}
      <div className="bg-[#0b1019] rounded-xl p-6 border border-slate-800 shadow-2xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-5 border-b border-slate-800">
          <div>
            <div className="flex items-center gap-2 text-xs text-emerald-400 uppercase tracking-widest font-semibold mb-1">
              <TrendingDown className="w-4 h-4" />
              <span>Dynamic RF Reduction Benchmark</span>
            </div>
            <h2 className="text-2xl font-bold text-slate-100 tracking-tight">
              COMMUNICATION BANDWIDTH & SIGNATURE METRICS
            </h2>
            <p className="text-xs text-slate-400 mt-1 max-w-2xl font-sans">
              Computed in real time using the mathematical formula: <code className="text-cyan-300">((Baseline - S.I.G.H.T.) / Baseline) × 100</code>.
            </p>
          </div>

          <div className="flex items-center gap-2 bg-emerald-950/30 border border-emerald-500/30 px-3.5 py-2 rounded-lg">
            <Zap className="w-4 h-4 text-emerald-400" />
            <div>
              <span className="text-[10px] text-slate-400 uppercase block leading-none">Overall Bandwidth Saved</span>
              <span className="text-lg font-bold text-emerald-400">-{bytesReduction}%</span>
            </div>
          </div>
        </div>

        {/* 3 Dynamic Reduction Bars */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
          {/* Bytes Reduction */}
          <div className="p-4 rounded-lg bg-[#0d1422] border border-slate-800/80 space-y-2">
            <div className="flex justify-between items-center text-xs">
              <span className="text-slate-400 uppercase flex items-center gap-1.5">
                <HardDrive className="w-3.5 h-3.5 text-cyan-400" />
                Data Volume Reduction
              </span>
              <span className="text-emerald-400 font-bold text-sm">-{bytesReduction}%</span>
            </div>
            <div className="w-full h-2.5 bg-slate-900 rounded-full overflow-hidden border border-slate-800">
              <div
                className="h-full bg-cyan-400 rounded-full transition-all duration-500"
                style={{ width: `${bytesReduction}%` }}
              />
            </div>
            <div className="text-[11px] text-slate-400 flex justify-between pt-1">
              <span>Saved: {formatBytes(metrics.baselineBytes - metrics.sightBytes)}</span>
              <span>{formatBytes(metrics.sightBytes)} radiated</span>
            </div>
          </div>

          {/* Packets Reduction */}
          <div className="p-4 rounded-lg bg-[#0d1422] border border-slate-800/80 space-y-2">
            <div className="flex justify-between items-center text-xs">
              <span className="text-slate-400 uppercase flex items-center gap-1.5">
                <Activity className="w-3.5 h-3.5 text-amber-400" />
                Packet Emission Reduction
              </span>
              <span className="text-amber-400 font-bold text-sm">-{packetsReduction}%</span>
            </div>
            <div className="w-full h-2.5 bg-slate-900 rounded-full overflow-hidden border border-slate-800">
              <div
                className="h-full bg-amber-400 rounded-full transition-all duration-500"
                style={{ width: `${packetsReduction}%` }}
              />
            </div>
            <div className="text-[11px] text-slate-400 flex justify-between pt-1">
              <span>Saved: {(metrics.baselinePackets - metrics.sightPackets).toLocaleString()} pkts</span>
              <span>{metrics.sightPackets} pkts radiated</span>
            </div>
          </div>

          {/* RF Airtime Duration Reduction */}
          <div className="p-4 rounded-lg bg-[#0d1422] border border-slate-800/80 space-y-2">
            <div className="flex justify-between items-center text-xs">
              <span className="text-slate-400 uppercase flex items-center gap-1.5">
                <Radio className="w-3.5 h-3.5 text-emerald-400" />
                Transmission Duration
              </span>
              <span className="text-emerald-400 font-bold text-sm">-{durationReduction}%</span>
            </div>
            <div className="w-full h-2.5 bg-slate-900 rounded-full overflow-hidden border border-slate-800">
              <div
                className="h-full bg-emerald-400 rounded-full transition-all duration-500"
                style={{ width: `${durationReduction}%` }}
              />
            </div>
            <div className="text-[11px] text-slate-400 flex justify-between pt-1">
              <span>Saved: {formatDuration(metrics.baselineDurationSec - metrics.sightDurationSec)}</span>
              <span>{formatDuration(metrics.sightDurationSec)} radiating</span>
            </div>
          </div>
        </div>
      </div>

      {/* Direct Comparison Table */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Baseline Card */}
        <div className="bg-[#0b1019] rounded-xl p-5 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div>
              <span className="text-xs text-slate-400 uppercase tracking-wider font-bold block">
                BASELINE (Continuous Polling)
              </span>
              <span className="text-[10px] text-slate-400 font-sans">
                Standard unmanaged UAV data stream without S.I.G.H.T.
              </span>
            </div>
            <span className="text-xs font-bold text-red-400 bg-red-950/30 px-2 py-0.5 rounded border border-red-800/40">
              HIGH RF EXPOSURE
            </span>
          </div>

          <div className="space-y-2.5 text-xs">
            <div className="p-3 rounded bg-[#0d1422] border border-slate-800 flex justify-between items-center">
              <span className="text-slate-400">Total Bytes Transmitted:</span>
              <span className="font-bold text-slate-100 text-sm">
                {formatBytes(metrics.baselineBytes)}
                <span className="text-[10px] text-slate-400 ml-1.5 font-normal">
                  ({metrics.baselineBytes.toLocaleString()} B)
                </span>
              </span>
            </div>

            <div className="p-3 rounded bg-[#0d1422] border border-slate-800 flex justify-between items-center">
              <span className="text-slate-400">Total Packets Emitted:</span>
              <span className="font-bold text-slate-100 text-sm">
                {metrics.baselinePackets.toLocaleString()} packets
              </span>
            </div>

            <div className="p-3 rounded bg-[#0d1422] border border-slate-800 flex justify-between items-center">
              <span className="text-slate-400">Transmission Airtime:</span>
              <span className="font-bold text-slate-100 text-sm">
                {formatDuration(metrics.baselineDurationSec)}
              </span>
            </div>
          </div>
        </div>

        {/* S.I.G.H.T. Card */}
        <div className="bg-[#0b1019] rounded-xl p-5 border border-cyan-900/40 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <div>
              <span className="text-xs text-cyan-400 uppercase tracking-wider font-bold block">
                S.I.G.H.T. GOVERNED TRANSMISSION
              </span>
              <span className="text-[10px] text-slate-400 font-sans">
                Mission-aware edge filter emitting only EVENT / EVIDENCE
              </span>
            </div>
            <span className="text-xs font-bold text-emerald-400 bg-emerald-950/30 px-2 py-0.5 rounded border border-emerald-800/40">
              LOW RF SIGNATURE
            </span>
          </div>

          <div className="space-y-2.5 text-xs">
            <div className="p-3 rounded bg-[#0d1422] border border-slate-800 flex justify-between items-center">
              <span className="text-slate-400">Total Bytes Transmitted:</span>
              <span className="font-bold text-cyan-300 text-sm">
                {formatBytes(metrics.sightBytes)}
                <span className="text-[10px] text-emerald-400 ml-1.5 font-normal">
                  (-{bytesReduction}%)
                </span>
              </span>
            </div>

            <div className="p-3 rounded bg-[#0d1422] border border-slate-800 flex justify-between items-center">
              <span className="text-slate-400">Total Packets Emitted:</span>
              <span className="font-bold text-cyan-300 text-sm">
                {metrics.sightPackets.toLocaleString()} packets
                <span className="text-[10px] text-emerald-400 ml-1.5 font-normal">
                  (-{packetsReduction}%)
                </span>
              </span>
            </div>

            <div className="p-3 rounded bg-[#0d1422] border border-slate-800 flex justify-between items-center">
              <span className="text-slate-400">Transmission Airtime:</span>
              <span className="font-bold text-cyan-300 text-sm">
                {formatDuration(metrics.sightDurationSec)}
                <span className="text-[10px] text-emerald-400 ml-1.5 font-normal">
                  (-{durationReduction}%)
                </span>
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Formula Documentation Card */}
      <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 text-xs text-slate-400 flex items-start gap-3">
        <Info className="w-5 h-5 text-cyan-400 shrink-0 mt-0.5" />
        <div className="font-sans space-y-1">
          <div className="font-bold text-slate-200 font-mono">Dynamic Performance Verification:</div>
          <p>
            No hardcoded efficiency claims. The reduction percentages update on every simulation tick as baseline continuous transmissions advance and S.I.G.H.T. selectively pulses only confirmed target events.
          </p>
        </div>
      </div>
    </div>
  );
};
