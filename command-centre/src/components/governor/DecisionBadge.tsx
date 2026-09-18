import React from 'react';
import { GovernorState } from '../../types';

interface DecisionBadgeProps {
  decision: GovernorState;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  pulse?: boolean;
}

export const DecisionBadge: React.FC<DecisionBadgeProps> = ({
  decision,
  size = 'md',
  pulse = false
}) => {
  const configs: Record<
    GovernorState,
    { bg: string; text: string; border: string; glow: string; desc: string }
  > = {
    EVENT: {
      bg: 'bg-cyan-500/15',
      text: 'text-cyan-300',
      border: 'border-cyan-500/50',
      glow: 'shadow-cyan-500/20',
      desc: 'Transmits compact event metadata'
    },
    RETAIN: {
      bg: 'bg-amber-500/15',
      text: 'text-amber-300',
      border: 'border-amber-500/50',
      glow: 'shadow-amber-500/20',
      desc: 'Cached locally in edge NVMe buffer'
    },
    SUPPRESS: {
      bg: 'bg-slate-700/30',
      text: 'text-slate-300',
      border: 'border-slate-600/50',
      glow: 'shadow-slate-500/10',
      desc: 'Discarded silently at edge. Zero RF emissions.'
    },
    EVIDENCE: {
      bg: 'bg-purple-500/15',
      text: 'text-purple-300',
      border: 'border-purple-500/50',
      glow: 'shadow-purple-500/20',
      desc: 'Image/clip payload prepared'
    }
  };

  const current = configs[decision] || configs.SUPPRESS;

  const sizeStyles = {
    sm: 'text-xs px-2 py-0.5 font-semibold',
    md: 'text-sm px-3 py-1 font-bold',
    lg: 'text-lg px-4 py-1.5 font-extrabold tracking-wider',
    xl: 'text-2xl px-6 py-2.5 font-black tracking-widest'
  };

  return (
    <div className="inline-flex flex-col items-center">
      <div
        className={`inline-flex items-center gap-2 rounded border uppercase font-mono shadow-lg ${current.bg} ${current.text} ${current.border} ${current.glow} ${sizeStyles[size]}`}
      >
        {pulse && (
          <span className="relative flex h-3 w-3">
            <span
              className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${
                decision === 'EVENT' ? 'bg-cyan-400' : 'bg-amber-400'
              }`}
            />
            <span
              className={`relative inline-flex rounded-full h-3 w-3 ${
                decision === 'EVENT' ? 'bg-cyan-400' : 'bg-amber-400'
              }`}
            />
          </span>
        )}
        <span>{decision}</span>
      </div>
    </div>
  );
};
