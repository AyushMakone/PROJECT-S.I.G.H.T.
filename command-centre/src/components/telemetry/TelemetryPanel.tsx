import React from 'react';
import { useSimulation } from '../../hooks/useSimulation';
import { MetricCard } from '../common/MetricCard';
import {
  Compass,
  Gauge,
  Battery,
  MapPin,
  Navigation,
  Activity,
  Plane,
  Satellite
} from 'lucide-react';

export const TelemetryPanel: React.FC = () => {
  const { telemetry, mission } = useSimulation();
  const live = telemetry.hasTelemetry;

  return (
    <div className="space-y-6 font-mono">
      {/* Flight Avionics Primary Readouts */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
        <MetricCard
          label="ALTITUDE AGL"
          value={live ? (telemetry.relativeAltitude ?? 'N/A') : '---'}
          unit="m AGL"
          subValue={live ? `Climb: ${telemetry.climbRate} m/s` : 'UNKNOWN'}
          icon={<Gauge className="w-4 h-4 text-cyan-400" />}
          variant="cyan"
        />

        <MetricCard
          label="GROUND SPEED"
          value={live ? telemetry.speed : '---'}
          unit="m/s"
          subValue={live ? `~${(telemetry.speed * 3.6).toFixed(0)} km/h` : 'UNKNOWN'}
          icon={<Plane className="w-4 h-4 text-cyan-400" />}
          variant="cyan"
        />

        <MetricCard
          label="HEADING"
          value={live ? telemetry.heading : '---'}
          unit={live ? `${telemetry.headingDegrees}°` : 'UNKNOWN'}
          subValue="True North Track"
          icon={<Compass className="w-4 h-4 text-amber-400" />}
          variant="amber"
        />

        <MetricCard
          label="BATTERY"
          value={live ? `${telemetry.battery}%` : '---'}
          subValue={live ? `${telemetry.batteryVoltage} V` : 'UNKNOWN'}
          icon={<Battery className="w-4 h-4 text-emerald-400" />}
          variant={!live ? 'default' : telemetry.battery < 25 ? 'crimson' : 'emerald'}
        />

        <MetricCard
          label="GPS FIX"
          value={live ? telemetry.gpsStatus : 'UNKNOWN'}
          subValue={live ? `${telemetry.gpsSatellites} Sats | HDOP ${telemetry.hdop}` : 'UNKNOWN'}
          icon={<Satellite className="w-4 h-4 text-emerald-400" />}
          variant="emerald"
        />

        <MetricCard
          label="FLIGHT MODE"
          value={live ? telemetry.flightMode : 'UNKNOWN'}
          subValue={live ? 'ArduPilot SITL' : 'WAITING FOR HEARTBEAT'}
          icon={<Navigation className="w-4 h-4 text-cyan-400" />}
          variant="default"
        />
      </div>

      {/* Synthetic Attitude & Navigation Compass Center */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Synthetic Horizon & Attitude Display */}
        <div className="bg-[#0b1019] rounded-xl p-5 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <span className="text-xs text-slate-400 uppercase tracking-wider font-bold flex items-center gap-2">
              <Activity className="w-4 h-4 text-cyan-400" />
              Attitude & Gyro
            </span>
            <span className="text-[10px] text-slate-400">IMU 6-DOF</span>
          </div>

          {/* Artificial Horizon Mock Graphic */}
          <div className="relative w-full h-48 bg-[#070b13] rounded-lg border border-slate-800 overflow-hidden flex items-center justify-center">
            {/* Horizon Sky & Ground */}
            <div
              className="absolute inset-0 transition-transform duration-300"
              style={{
                transform: `rotate(${-telemetry.roll}deg) translateY(${telemetry.pitch * 3}px)`
              }}
            >
              <div className="h-1/2 bg-blue-950/40 border-b-2 border-cyan-400 flex items-end justify-center pb-1">
                <span className="text-[9px] text-cyan-400 opacity-60">SKY</span>
              </div>
              <div className="h-1/2 bg-amber-950/30 flex items-start justify-center pt-1">
                <span className="text-[9px] text-amber-500 opacity-60">GROUND</span>
              </div>
            </div>

            {/* Aircraft Fixed Reticle */}
            <div className="relative z-10 w-24 h-1 border-t-2 border-amber-400 flex items-center justify-center">
              <div className="w-3 h-3 rounded-full border-2 border-amber-400 -mt-2 bg-[#0b1019]" />
            </div>

            {/* Pitch & Roll Numerical Tags */}
            <div className="absolute top-2 left-2 text-[10px] bg-black/60 px-1.5 py-0.5 rounded text-slate-300">
              PITCH: {telemetry.pitch > 0 ? `+${telemetry.pitch}` : telemetry.pitch}°
            </div>
            <div className="absolute top-2 right-2 text-[10px] bg-black/60 px-1.5 py-0.5 rounded text-slate-300">
              ROLL: {telemetry.roll > 0 ? `+${telemetry.roll}` : telemetry.roll}°
            </div>
            <div className="absolute bottom-2 left-2 text-[10px] bg-black/60 px-1.5 py-0.5 rounded text-slate-300">
              YAW: {telemetry.yaw}°
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2 text-center text-xs">
            <div className="p-2 rounded bg-[#0d1422] border border-slate-800">
              <span className="text-[10px] text-slate-400 block">PITCH</span>
              <span className="font-bold text-slate-200">{telemetry.pitch}°</span>
            </div>
            <div className="p-2 rounded bg-[#0d1422] border border-slate-800">
              <span className="text-[10px] text-slate-400 block">ROLL</span>
              <span className="font-bold text-slate-200">{telemetry.roll}°</span>
            </div>
            <div className="p-2 rounded bg-[#0d1422] border border-slate-800">
              <span className="text-[10px] text-slate-400 block">YAW</span>
              <span className="font-bold text-slate-200">{telemetry.yaw}°</span>
            </div>
          </div>
        </div>

        {/* Circular Compass Rose & Nav Heading */}
        <div className="bg-[#0b1019] rounded-xl p-5 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <span className="text-xs text-slate-400 uppercase tracking-wider font-bold flex items-center gap-2">
              <Compass className="w-4 h-4 text-amber-400" />
              Compass Rose & Track
            </span>
            <span className="text-[10px] text-amber-400 font-bold">{telemetry.heading} ({telemetry.headingDegrees}°)</span>
          </div>

          <div className="relative w-full h-48 flex items-center justify-center">
            {/* Compass Dial */}
            <div
              className="relative w-40 h-40 rounded-full border-2 border-slate-800 bg-[#070b13] flex items-center justify-center transition-transform duration-300"
              style={{ transform: `rotate(${-telemetry.headingDegrees}deg)` }}
            >
              {/* Cardinal Markers */}
              <span className="absolute top-1.5 text-xs font-bold text-red-400">N</span>
              <span className="absolute right-2 text-xs font-bold text-slate-400">E</span>
              <span className="absolute bottom-1.5 text-xs font-bold text-slate-400">S</span>
              <span className="absolute left-2 text-xs font-bold text-slate-400">W</span>

              {/* Ticks */}
              <div className="w-32 h-32 rounded-full border border-dashed border-slate-800" />
            </div>

            {/* Fixed Heading Lubber Line */}
            <div className="absolute top-3 w-0.5 h-6 bg-cyan-400 shadow-[0_0_8px_#22d3ee]" />

            {/* Aircraft silhouette at center */}
            <div className="absolute w-8 h-8 flex items-center justify-center text-cyan-400">
              <Plane className="w-6 h-6" />
            </div>
          </div>

          <div className="p-2.5 rounded bg-[#0d1422] border border-slate-800 text-center text-xs">
            <span className="text-slate-400 text-[10px] uppercase block">CURRENT HEADING</span>
            <span className="font-bold text-cyan-400">{live ? `${telemetry.headingDegrees}° TRUE NORTH` : 'N/A'}</span>
          </div>
        </div>

        {/* Geographic Coordinates & Link Status */}
        <div className="bg-[#0b1019] rounded-xl p-5 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <span className="text-xs text-slate-400 uppercase tracking-wider font-bold flex items-center gap-2">
              <MapPin className="w-4 h-4 text-emerald-400" />
              GNSS & Radio Link
            </span>
            <span className="text-[10px] text-slate-400 font-bold">GNSS STATUS</span>
          </div>

          <div className="space-y-2.5 text-xs">
            <div className="p-3 rounded bg-[#0d1422] border border-slate-800">
              <span className="text-slate-400 text-[10px] block uppercase">LATITUDE / LONGITUDE</span>
              <span className="font-bold text-slate-100 text-sm">
                {telemetry.lat.toFixed(5)}° N, {Math.abs(telemetry.lng).toFixed(5)}° W
              </span>
            </div>

            <div className="p-3 rounded bg-[#0d1422] border border-slate-800">
              <span className="text-slate-400 text-[10px] block uppercase">RADIO LINK STATUS</span>
              <div className="flex items-center justify-between mt-1">
                <span className="font-bold text-emerald-400">{telemetry.linkStatus}</span>
                <span className="text-slate-300">RSSI: {telemetry.rssi} dBm</span>
              </div>
            </div>

            <div className="p-3 rounded bg-[#0d1422] border border-slate-800">
              <span className="text-slate-400 text-[10px] block uppercase">ASSIGNED UAV PLATFORM</span>
              <span className="font-bold text-cyan-300">{mission.uavId} (PX4 Autopilot SITL)</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
