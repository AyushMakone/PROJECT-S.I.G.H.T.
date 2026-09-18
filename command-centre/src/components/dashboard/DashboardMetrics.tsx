import React from 'react';
import { useSimulation } from '../../hooks/useSimulation';
import { TrendingDown, ArrowRight, Radio } from 'lucide-react';
import { Link } from 'react-router-dom';

export const DashboardMetrics: React.FC = () => {
  const { metrics, communication } = useSimulation();

  const calcReduction = (baseline: number, sight: number): number => {
    if (baseline <= 0) return 0;
    const red = ((baseline - sight) / baseline) * 100;
    return Math.max(0, Math.min(100, Number(red.toFixed(1))));
  };

  const bytesRed = calcReduction(metrics.baselineBytes, metrics.sightBytes);
  const packetsRed = calcReduction(metrics.baselinePackets, metrics.sightPackets);
  const airtimeRed = calcReduction(metrics.baselineDurationSec, metrics.sightDurationSec);

  return (
    <div className="bg-[#0b1019] rounded-xl p-4 border border-slate-800 font-mono">
      <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <TrendingDown className="w-4 h-4 text-emerald-400" />
          <span className="text-xs text-slate-300 font-bold uppercase tracking-wider">
            S.I.G.H.T. RF REDUCTION METRICS
          </span>
        </div>
        <Link
          to="/communications"
          className="text-[11px] text-cyan-400 hover:text-cyan-300 flex items-center gap-1 transition-colors"
        >
          <span>Link Analytics</span>
          <ArrowRight className="w-3 h-3" />
        </Link>
      </div>

      <div className="grid grid-cols-3 gap-3 text-center">
        <div className="p-2.5 rounded bg-[#0d1422] border border-slate-800">
          <span className="text-[10px] text-slate-400 block uppercase">BANDWIDTH</span>
          <span className="text-lg font-bold text-emerald-400">-{bytesRed}%</span>
          <span className="text-[10px] text-slate-400 block">Data Volume</span>
        </div>

        <div className="p-2.5 rounded bg-[#0d1422] border border-slate-800">
          <span className="text-[10px] text-slate-400 block uppercase">RF BURSTS</span>
          <span className="text-lg font-bold text-cyan-400">-{packetsRed}%</span>
          <span className="text-[10px] text-slate-400 block">{communication.packets} Transmitted</span>
        </div>

        <div className="p-2.5 rounded bg-[#0d1422] border border-slate-800">
          <span className="text-[10px] text-slate-400 block uppercase">AIRTIME</span>
          <span className="text-lg font-bold text-amber-400">-{airtimeRed}%</span>
          <span className="text-[10px] text-slate-400 block">{communication.transmissionDurationSec}s Total</span>
        </div>
      </div>
    </div>
  );
};
