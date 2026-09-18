import React from 'react';
import { Detection } from '../../types';
import { DecisionBadge } from '../governor/DecisionBadge';
import { User, Car, PawPrint, Shield, MapPin, Gauge } from 'lucide-react';

interface AIEventCardProps {
  detection: Detection;
  onSelect?: (detection: Detection) => void;
  isSelected?: boolean;
}

export const AIEventCard: React.FC<AIEventCardProps> = ({
  detection,
  onSelect,
  isSelected = false
}) => {
  const getObjectIcon = (obj: string) => {
    switch (obj) {
      case 'Person':
        return <User className="w-4 h-4 text-purple-400" />;
      case 'Vehicle':
        return <Car className="w-4 h-4 text-cyan-400" />;
      case 'Animal':
        return <PawPrint className="w-4 h-4 text-amber-400" />;
      default:
        return <Shield className="w-4 h-4 text-slate-400" />;
    }
  };

  const getConfidenceColor = (conf: number) => {
    if (conf >= 85) return 'text-emerald-400';
    if (conf >= 70) return 'text-cyan-400';
    return 'text-amber-400';
  };

  return (
    <div
      onClick={() => onSelect?.(detection)}
      className={`bg-[#0b1019] rounded-xl p-4 border transition-all duration-150 cursor-pointer ${
        isSelected
          ? 'border-cyan-500/80 bg-[#0e1625] shadow-lg shadow-cyan-950/40'
          : 'border-slate-800/90 hover:border-slate-700 hover:bg-[#0d1421]'
      }`}
    >
      {/* Header Row */}
      <div className="flex items-center justify-between gap-2 mb-2 font-mono">
        <div className="flex items-center gap-2">
          <span className="p-1.5 rounded bg-slate-800/80 border border-slate-700/80">
            {getObjectIcon(detection.object)}
          </span>
          <div>
            <span className="font-bold text-slate-100 text-sm uppercase tracking-wide">
              {detection.object}
            </span>
            <span className="text-[10px] text-slate-400 ml-2 font-normal">
              {detection.id}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="text-right">
            <span className="text-[10px] text-slate-400 block leading-none uppercase">Confidence</span>
            <span className={`text-xs font-bold ${getConfidenceColor(detection.confidence)}`}>
              {detection.confidence}%
            </span>
          </div>
          <span className="text-[11px] text-slate-400 font-mono bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
            {detection.timestamp}
          </span>
        </div>
      </div>

      {/* Details Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs font-mono my-2.5 pt-2 border-t border-slate-800/60 text-slate-300">
        <div className="flex items-center gap-1.5 truncate">
          <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
          <span className="truncate">{detection.locationName}</span>
        </div>

        <div className="flex items-center gap-1.5">
          <Gauge className="w-3.5 h-3.5 text-slate-400 shrink-0" />
          <span className="text-slate-400">Persistence:</span>
          <span className="font-bold text-slate-200">{detection.persistence} frames</span>
        </div>
      </div>

      {/* Footer / Governor Decision Row */}
      <div className="mt-2.5 pt-2.5 border-t border-slate-800/80 flex items-center justify-between">
        <div className="flex items-center gap-2 font-mono text-[11px]">
          <span className="text-slate-400 uppercase">Zone:</span>
          <span
            className={`font-semibold ${
              detection.insidePriorityZone
                ? 'text-red-400'
                : 'text-slate-400'
            }`}
          >
            {detection.zone}
          </span>
        </div>

        <div className="flex items-center gap-2">
          <span className="text-[10px] font-mono text-slate-400 uppercase">Decision:</span>
          <DecisionBadge decision={detection.governorDecision} size="sm" />
        </div>
      </div>
    </div>
  );
};
