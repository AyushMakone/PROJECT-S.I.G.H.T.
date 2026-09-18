import React from 'react';

export type BadgeVariant = 'emerald' | 'amber' | 'cyan' | 'crimson' | 'violet' | 'slate';

interface StatusBadgeProps {
  label: string;
  variant?: BadgeVariant;
  pulse?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  label,
  variant = 'emerald',
  pulse = false,
  size = 'md',
  className = ''
}) => {
  const variantStyles = {
    emerald: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30',
    amber: 'bg-amber-500/10 text-amber-400 border-amber-500/30',
    cyan: 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30',
    crimson: 'bg-red-500/10 text-red-400 border-red-500/30',
    violet: 'bg-purple-500/10 text-purple-400 border-purple-500/30',
    slate: 'bg-slate-500/10 text-slate-400 border-slate-500/30'
  };

  const dotColors = {
    emerald: 'bg-emerald-400',
    amber: 'bg-amber-400',
    cyan: 'bg-cyan-400',
    crimson: 'bg-red-400',
    violet: 'bg-purple-400',
    slate: 'bg-slate-400'
  };

  const sizeStyles = {
    sm: 'text-xs px-2 py-0.5 tracking-wider',
    md: 'text-xs px-2.5 py-1 tracking-widest font-semibold',
    lg: 'text-sm px-3.5 py-1.5 tracking-widest font-bold'
  };

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded border uppercase font-mono ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
    >
      <span className="relative flex h-2 w-2">
        {pulse && (
          <span
            className={`animate-ping absolute inline-flex h-full w-full rounded-full opacity-75 ${dotColors[variant]}`}
          />
        )}
        <span className={`relative inline-flex rounded-full h-2 w-2 ${dotColors[variant]}`} />
      </span>
      {label}
    </span>
  );
};
