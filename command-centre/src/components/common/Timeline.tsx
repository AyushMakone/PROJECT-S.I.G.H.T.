import React, { useState } from 'react';
import { TimelineEvent } from '../../types';
import { Clock, Radio, Eye, Plane, ShieldCheck } from 'lucide-react';

interface TimelineProps {
  events: TimelineEvent[];
  maxItems?: number;
  className?: string;
  showFilters?: boolean;
}

export const Timeline: React.FC<TimelineProps> = ({
  events,
  maxItems = 10,
  className = '',
  showFilters = false
}) => {
  const [filter, setFilter] = useState<string>('ALL');

  const filteredEvents = events.filter(e => {
    if (filter === 'ALL') return true;
    return e.category === filter;
  }).slice(0, maxItems);

  const getCategoryIcon = (category: TimelineEvent['category']) => {
    switch (category) {
      case 'MISSION':
      case 'GOVERNOR':
        return <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />;
      case 'COMMUNICATION':
        return <Radio className="w-3.5 h-3.5 text-emerald-400" />;
      case 'DETECTION':
        return <Eye className="w-3.5 h-3.5 text-amber-400" />;
      case 'FLIGHT':
        return <Plane className="w-3.5 h-3.5 text-blue-400" />;
      default:
        return <Clock className="w-3.5 h-3.5 text-slate-400" />;
    }
  };

  const getDotColor = (level: TimelineEvent['level']) => {
    switch (level) {
      case 'success':
        return 'bg-emerald-400 border-emerald-500/40 shadow-emerald-500/20';
      case 'warning':
        return 'bg-amber-400 border-amber-500/40 shadow-amber-500/20';
      case 'alert':
        return 'bg-red-400 border-red-500/40 shadow-red-500/20';
      default:
        return 'bg-cyan-400 border-cyan-500/40 shadow-cyan-500/20';
    }
  };

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {showFilters && (
        <div className="flex items-center gap-1.5 mb-3 pb-2 border-b border-slate-800/80 text-[11px] font-mono overflow-x-auto">
          {['ALL', 'GOVERNOR', 'COMMUNICATION', 'DETECTION', 'FLIGHT'].map(cat => (
            <button
              key={cat}
              onClick={() => setFilter(cat)}
              className={`px-2 py-0.5 rounded transition-colors ${
                filter === cat
                  ? 'bg-slate-700 text-white font-semibold'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      )}

      <div className="relative pl-4 space-y-3.5 overflow-y-auto pr-1 flex-1">
        {/* Continuous vertical timeline track */}
        <div className="absolute left-[7px] top-1.5 bottom-2 w-px bg-slate-800" />

        {filteredEvents.map((evt) => (
          <div key={evt.id} className="relative group text-left">
            {/* Timeline node */}
            <div
              className={`absolute -left-4 top-1 w-2.5 h-2.5 rounded-full border shadow-sm ${getDotColor(
                evt.level
              )}`}
            />

            <div className="flex items-baseline justify-between gap-2">
              <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-200 group-hover:text-cyan-300 transition-colors">
                {getCategoryIcon(evt.category)}
                <span>{evt.title}</span>
              </div>
              <span className="text-[10px] font-mono text-slate-400 shrink-0">
                {evt.timestamp}
              </span>
            </div>

            {evt.detail && (
              <p className="text-[11px] text-slate-400 mt-0.5 leading-relaxed font-sans">
                {evt.detail}
              </p>
            )}
          </div>
        ))}

        {filteredEvents.length === 0 && (
          <div className="text-center py-6 text-xs text-slate-400 font-mono">
            NO TIMELINE EVENTS RECORDED
          </div>
        )}
      </div>
    </div>
  );
};
