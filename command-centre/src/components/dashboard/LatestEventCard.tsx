import React from 'react';
import { useSimulation } from '../../hooks/useSimulation';
import { DecisionBadge } from '../governor/DecisionBadge';
import { Eye, ArrowRight, MapPin, Gauge } from 'lucide-react';
import { Link } from 'react-router-dom';

export const LatestEventCard: React.FC = () => {
  const { detections } = useSimulation();
  const latest = detections[0];

  if (!latest) return null;

  return (
    <div className="bg-[#0b1019] rounded-xl p-4 border border-slate-800 font-mono flex flex-col justify-between">
      <div>
        <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800">
          <div className="flex items-center gap-2">
            <Eye className="w-4 h-4 text-amber-400" />
            <span className="text-xs text-slate-300 font-bold uppercase tracking-wider">
              LATEST AI EVENT
            </span>
          </div>
          <Link
            to="/ai-events"
            className="text-[11px] text-cyan-400 hover:text-cyan-300 flex items-center gap-1 transition-colors"
          >
            <span>Feed ({detections.length})</span>
            <ArrowRight className="w-3 h-3" />
          </Link>
        </div>

        <div className="flex items-center justify-between gap-2 mb-2">
          <div className="flex items-center gap-2">
            <span className="text-lg font-bold text-slate-100 uppercase">{latest.object}</span>
            <span className="text-xs text-emerald-400 font-bold bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-800/40">
              {latest.confidence}%
            </span>
          </div>
          <span className="text-[11px] text-slate-400">{latest.timestamp}</span>
        </div>

        <div className="space-y-1.5 text-xs text-slate-300 pt-2 border-t border-slate-800/60">
          <div className="flex items-center gap-1.5 truncate">
            <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <span className="truncate">{latest.locationName}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Gauge className="w-3.5 h-3.5 text-slate-400 shrink-0" />
            <span className="text-slate-400">Persistence:</span>
            <span className="font-bold text-slate-200">{latest.persistence} frames</span>
          </div>
        </div>
      </div>

      <div className="mt-3 pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs">
        <span className="text-[11px] text-slate-400 uppercase">Governor Decision:</span>
        <DecisionBadge decision={latest.governorDecision} size="sm" />
      </div>
    </div>
  );
};
