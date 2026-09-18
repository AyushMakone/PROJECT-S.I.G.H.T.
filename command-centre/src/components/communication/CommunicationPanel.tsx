import React from 'react';
import { useSimulation } from '../../hooks/useSimulation';
import { StatusBadge } from '../common/StatusBadge';
import { MetricCard } from '../common/MetricCard';
import { Radio, Wifi, Activity, ShieldAlert, Cpu, AlertTriangle } from 'lucide-react';

export const CommunicationPanel: React.FC = () => {
  const { communication } = useSimulation();

  const formattedBytes = (bytes: number) => {
    if (bytes >= 1048576) return `${(bytes / 1048576).toFixed(2)} MB`;
    return `${(bytes / 1024).toFixed(0)} KB`;
  };

  return (
    <div className="space-y-6">
      {/* Critical Mandatory Label & Safety Notice */}
      <div className="bg-[#0b1019] rounded-xl p-6 border border-slate-800 shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-5 border-b border-slate-800">
          <div>
            <div className="flex items-center gap-2 text-xs font-mono text-cyan-400 uppercase tracking-widest font-semibold mb-1">
              <Radio className="w-4 h-4" />
              <span>Tactical Data Link Governance</span>
            </div>
            <h2 className="text-2xl font-bold font-mono text-slate-100 tracking-tight">
              MISSION-DATA COMMUNICATION
            </h2>
            <p className="text-xs text-slate-400 mt-1 max-w-2xl font-sans">
              Autonomous edge controller managing mission payload emissions. Critical UAV flight-safety C2 / telemetry remains separate and autonomous.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <div className="text-right font-mono">
              <span className="text-[10px] text-slate-400 block uppercase">LINK STATUS</span>
              <StatusBadge
                label={communication.status}
                variant={communication.status === 'ACTIVE' ? 'cyan' : 'slate'}
                pulse={communication.status === 'ACTIVE'}
                size="lg"
              />
            </div>
          </div>
        </div>

        {/* Primary Link Metrics Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 font-mono mt-5">
          <MetricCard
            label="STATUS"
            value={communication.status}
            variant={communication.status === 'ACTIVE' ? 'cyan' : 'default'}
          />
          <MetricCard
            label="PACKETS"
            value={communication.packets}
            subValue="Transmitted"
            variant="cyan"
          />
          <MetricCard
            label="DATA VOLUME"
            value={formattedBytes(communication.bytes)}
            subValue={`${communication.bytes.toLocaleString()} bytes`}
            variant="emerald"
          />
          <MetricCard
            label="TX DURATION"
            value={communication.transmissionDurationSec}
            unit="sec"
            subValue="RF Radiating Time"
            variant="amber"
          />
          <MetricCard
            label="LAST TX TIME"
            value={communication.lastTransmission.split(' ')[0] || '19:42:09'}
            unit="UTC"
            subValue="Most recent burst"
          />
          <MetricCard
            label="PACKET TYPE"
            value={communication.lastPacketType}
            subValue="Payload format"
            variant={communication.lastPacketType === 'EVENT' ? 'cyan' : 'default'}
          />
        </div>
      </div>

      {/* RF Signature & Stealth Meter */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* RF Emission Duty Cycle */}
        <div className="bg-[#0b1019] rounded-xl p-5 border border-slate-800 font-mono space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <span className="text-xs text-slate-400 uppercase tracking-wider font-bold flex items-center gap-2">
              <Activity className="w-4 h-4 text-emerald-400" />
              RF Stealth & Duty Cycle
            </span>
            <span className="text-xs text-emerald-400 font-bold">
              {communication.rfSilencePercent}% SILENT
            </span>
          </div>

          <div>
            <div className="flex justify-between text-xs mb-1.5">
              <span className="text-slate-400">Radio Frequency Emission Time</span>
              <span className="text-amber-400 font-bold">{communication.dutyCyclePercent}%</span>
            </div>
            <div className="w-full h-3 bg-slate-900 rounded-full overflow-hidden border border-slate-800">
              <div
                className="h-full bg-gradient-to-r from-cyan-500 to-amber-500 rounded-full transition-all duration-500"
                style={{ width: `${communication.dutyCyclePercent}%` }}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs pt-2">
            <div className="p-3 rounded bg-[#0d1422] border border-slate-800">
              <span className="text-slate-400 text-[10px] block uppercase">RADIO CHANNEL</span>
              <span className="text-slate-200 font-bold">{communication.channelFrequency}</span>
            </div>
            <div className="p-3 rounded bg-[#0d1422] border border-slate-800">
              <span className="text-slate-400 text-[10px] block uppercase">SNR LINK MARGIN</span>
              <span className="text-emerald-400 font-bold">+{communication.snr} dB</span>
            </div>
          </div>

          <p className="text-xs text-slate-400 font-sans leading-relaxed">
            S.I.G.H.T. suppresses over 95% of background detections at the edge, drastically minimizing the UAV's electromagnetic radio emission footprint.
          </p>
        </div>

        {/* Packet Architecture & Transmission Policy */}
        <div className="bg-[#0b1019] rounded-xl p-5 border border-slate-800 font-mono space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <span className="text-xs text-slate-400 uppercase tracking-wider font-bold flex items-center gap-2">
              <Cpu className="w-4 h-4 text-cyan-400" />
              Packet Types & Emission Policy
            </span>
            <span className="text-[10px] text-slate-400">MISSION LINK PROTOCOL</span>
          </div>

          <div className="space-y-2.5 text-xs">
            <div className="p-3 rounded bg-[#0d1422] border border-slate-800/80 flex items-start justify-between">
              <div>
                <div className="font-bold text-cyan-300 flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-cyan-400" />
                  EVENT PACKET (Active)
                </div>
                <div className="text-slate-400 mt-1 text-[11px] font-sans">
                  Compact 420-byte binary packet containing target class, confidence score, coordinate vector, and timestamp.
                </div>
              </div>
              <span className="text-[10px] text-emerald-400 font-bold bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-800/40">
                ENABLED
              </span>
            </div>

            <div className="p-3 rounded bg-[#0d1422] border border-slate-800/80 flex items-start justify-between">
              <div>
                <div className="font-bold text-purple-300 flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-purple-400" />
                  EVIDENCE PACKET (On Demand)
                </div>
                <div className="text-slate-400 mt-1 text-[11px] font-sans">
                  Compressed visual snapshot / bounding box crop (1.2–2.0 MB) emitted only when required by Mission Card.
                </div>
              </div>
              <span className="text-[10px] text-slate-400 font-bold bg-slate-900 px-2 py-0.5 rounded border border-slate-800">
                STANDBY
              </span>
            </div>
          </div>

          <div className="flex items-start gap-2 p-3 rounded bg-amber-950/20 border border-amber-800/40 text-[11px] text-amber-300 font-sans">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
            <div>
              <strong>Safety Isolation Principle:</strong> "INACTIVE" refers strictly to mission payload communication. Critical command & control telemetry operates on an independent fallback channel.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
