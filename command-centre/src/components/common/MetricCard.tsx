import React from 'react';

interface MetricCardProps {
  label: string;
  value: string | number;
  unit?: string;
  subValue?: string;
  icon?: React.ReactNode;
  variant?: 'default' | 'emerald' | 'cyan' | 'amber' | 'crimson';
  className?: string;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  label,
  value,
  unit,
  subValue,
  icon,
  variant = 'default',
  className = ''
}) => {
  const borderColors = {
    default: 'border-slate-800/80 hover:border-slate-700',
    emerald: 'border-emerald-500/30 hover:border-emerald-500/50',
    cyan: 'border-cyan-500/30 hover:border-cyan-500/50',
    amber: 'border-amber-500/30 hover:border-amber-500/50',
    crimson: 'border-red-500/30 hover:border-red-500/50'
  };

  const textColors = {
    default: 'text-slate-100',
    emerald: 'text-emerald-400',
    cyan: 'text-cyan-400',
    amber: 'text-amber-400',
    crimson: 'text-red-400'
  };

  return (
    <div
      className={`bg-[#0d131f]/90 rounded-lg p-3.5 border transition-all duration-200 flex flex-col justify-between ${borderColors[variant]} ${className}`}
    >
      <div className="flex items-center justify-between text-xs text-slate-400 font-mono tracking-wider uppercase mb-1">
        <span>{label}</span>
        {icon && <span className="text-slate-400 opacity-80">{icon}</span>}
      </div>
      <div className="flex items-baseline gap-1.5 my-0.5">
        <span className={`text-2xl font-bold font-mono tracking-tight ${textColors[variant]}`}>
          {value}
        </span>
        {unit && <span className="text-xs text-slate-400 font-mono">{unit}</span>}
      </div>
      {subValue && (
        <div className="text-[11px] text-slate-400 font-mono mt-1 pt-1 border-t border-slate-800/60 truncate">
          {subValue}
        </div>
      )}
    </div>
  );
};
