import React from 'react';
import { NavLink } from 'react-router-dom';
import { useSimulation } from '../../hooks/useSimulation';
import {
  LayoutDashboard,
  FileSpreadsheet,
  Map as MapIcon,
  Eye,
  ShieldAlert,
  Radio,
  Gauge,
  FolderLock,
  Cpu,
  Settings as SettingsIcon,
  Flame
} from 'lucide-react';

interface SidebarProps {
  collapsed?: boolean;
}

export const Sidebar: React.FC<SidebarProps> = () => {
  const { detections, evidence, governor, communication } = useSimulation();

  const navItems = [
    {
      to: '/',
      label: 'Dashboard',
      icon: <LayoutDashboard className="w-4 h-4" />,
      badge: null
    },
    {
      to: '/mission',
      label: 'Mission Card',
      icon: <FileSpreadsheet className="w-4 h-4" />,
      badge: 'ACTIVE'
    },
    {
      to: '/map',
      label: 'Tactical Map',
      icon: <MapIcon className="w-4 h-4" />,
      badge: null
    },
    {
      to: '/ai-events',
      label: 'AI Events',
      icon: <Eye className="w-4 h-4" />,
      badge: detections.length.toString()
    },
    {
      to: '/governor',
      label: 'S.I.G.H.T. Governor',
      icon: <ShieldAlert className="w-4 h-4" />,
      badge: governor.decision,
      badgeColor:
        governor.decision === 'EVENT'
          ? 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30'
          : governor.decision === 'RETAIN'
          ? 'bg-amber-500/20 text-amber-400 border-amber-500/30'
          : 'bg-slate-700 text-slate-300'
    },
    {
      to: '/communications',
      label: 'Communications',
      icon: <Radio className="w-4 h-4" />,
      badge: communication.status,
      badgeColor:
        communication.status === 'ACTIVE'
          ? 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30 animate-pulse'
          : 'bg-slate-800 text-slate-400 border-slate-700'
    },
    {
      to: '/telemetry',
      label: 'UAV Telemetry',
      icon: <Gauge className="w-4 h-4" />,
      badge: null
    },
    {
      to: '/evidence',
      label: 'Evidence Vault',
      icon: <FolderLock className="w-4 h-4" />,
      badge: evidence.length.toString()
    },
    {
      to: '/simulator',
      label: 'SITL Simulator',
      icon: <Cpu className="w-4 h-4" />,
      badge: 'SITL'
    },
    {
      to: '/settings',
      label: 'Settings',
      icon: <SettingsIcon className="w-4 h-4" />,
      badge: null
    }
  ];

  return (
    <aside className="w-60 bg-[#080c14] border-r border-slate-800/80 flex flex-col justify-between select-none shrink-0 h-full">
      <div className="py-3">
        <div className="px-4 mb-2 text-[10px] font-mono uppercase tracking-widest text-slate-400 font-bold">
          Navigation
        </div>
        <nav className="space-y-0.5 px-2">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) =>
                `flex items-center justify-between px-3 py-2 rounded-md text-xs font-medium transition-all duration-150 group ${
                  isActive
                    ? 'bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 shadow-sm shadow-cyan-950/50'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-[#0f1624] border border-transparent'
                }`
              }
            >
              <div className="flex items-center gap-2.5">
                <span className="text-slate-400 group-hover:text-cyan-400 transition-colors">
                  {item.icon}
                </span>
                <span>{item.label}</span>
              </div>

              {item.badge && (
                <span
                  className={`text-[9px] font-mono px-1.5 py-0.5 rounded border uppercase font-semibold ${
                    item.badgeColor || 'bg-slate-800 text-slate-400 border-slate-700'
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </NavLink>
          ))}
        </nav>
      </div>

      {/* Stealth Mode Indicator Footer */}
      <div className="p-3 border-t border-slate-800/80 bg-[#06090f]">
        <div className="p-2.5 rounded bg-slate-900/90 border border-slate-800 flex items-center gap-2.5">
          <div className="w-7 h-7 rounded bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 shrink-0">
            <Flame className="w-3.5 h-3.5" />
          </div>
          <div className="overflow-hidden">
            <div className="text-[10px] text-slate-400 uppercase font-mono tracking-wider">
              RF Emission Policy
            </div>
            <div className="text-xs font-mono font-bold text-emerald-400 truncate">
              SILENT GOVERNANCE
            </div>
          </div>
        </div>
      </div>
    </aside>
  );
};
