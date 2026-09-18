import React from 'react';
import { useSimulation } from '../../hooks/useSimulation';
import { StatusBadge } from '../common/StatusBadge';
import {
  Gauge,
  Compass,
  BatteryCharging,
  Satellite,
  Radio,
  Activity,
  Plane
} from 'lucide-react';

export const UAVStatus: React.FC = () => {
  const { telemetry, communication } = useSimulation();

  return (
    <div className="bg-[#0b1019] rounded-xl p-4 border border-slate-800 font-mono">
      <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <Plane className="w-4 h-4 text-cyan-400" />
          <span className="text-xs text-slate-300 font-bold uppercase tracking-wider">
            UAV AVIONICS & LINK
          </span>
        </div>
        <StatusBadge label={telemetry.systemStatus} variant="emerald" size="sm" pulse={true} />
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 text-xs">
        {/* Altitude */}
        <div className="p-2 rounded bg-[#0d1422] border border-slate-800/80">
          <span className="text-[10px] text-slate-400 block uppercase">Altitude</span>
          <span className="text-sm font-bold text-slate-100">{telemetry.altitude} m</span>
          <span className="text-[10px] text-slate-400 block">+0.1 m/s</span>
        </div>

        {/* Speed */}
        <div className="p-2 rounded bg-[#0d1422] border border-slate-800/80">
          <span className="text-[10px] text-slate-400 block uppercase">Speed</span>
          <span className="text-sm font-bold text-slate-100">{telemetry.speed} m/s</span>
          <span className="text-[10px] text-slate-400 block">Ground Track</span>
        </div>

        {/* Heading */}
        <div className="p-2 rounded bg-[#0d1422] border border-slate-800/80">
          <span className="text-[10px] text-slate-400 block uppercase">Heading</span>
          <span className="text-sm font-bold text-amber-400">{telemetry.heading}</span>
          <span className="text-[10px] text-slate-400 block">{telemetry.headingDegrees}° Mag</span>
        </div>

        {/* Battery */}
        <div className="p-2 rounded bg-[#0d1422] border border-slate-800/80">
          <span className="text-[10px] text-slate-400 block uppercase">Battery</span>
          <span
            className={`text-sm font-bold ${
              telemetry.battery < 25 ? 'text-red-400' : 'text-emerald-400'
            }`}
          >
            {telemetry.battery}%
          </span>
          <span className="text-[10px] text-slate-400 block">{telemetry.batteryVoltage} V</span>
        </div>

        {/* GPS Status */}
        <div className="p-2 rounded bg-[#0d1422] border border-slate-800/80">
          <span className="text-[10px] text-slate-400 block uppercase">GPS Fix</span>
          <span className="text-sm font-bold text-emerald-400">{telemetry.gpsStatus}</span>
          <span className="text-[10px] text-slate-400 block">{telemetry.gpsSatellites} Sats</span>
        </div>

        {/* Mission Comm */}
        <div className="p-2 rounded bg-[#0d1422] border border-slate-800/80">
          <span className="text-[10px] text-slate-400 block uppercase">Comm Link</span>
          <span
            className={`text-sm font-bold ${
              communication.status === 'ACTIVE'
                ? 'text-cyan-400 animate-pulse'
                : 'text-slate-400'
            }`}
          >
            {communication.status}
          </span>
          <span className="text-[10px] text-slate-400 block">{communication.packets} Pkts</span>
        </div>
      </div>
    </div>
  );
};
