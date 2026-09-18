import React, { useState } from 'react';
import { useSimulation } from '../../hooks/useSimulation';
import { EvidenceItem } from '../../types';
import { FolderLock, Crosshair } from 'lucide-react';

export const EvidencePanel: React.FC = () => {
  const { evidence, mission } = useSimulation();
  const [selectedItem, setSelectedItem] = useState<EvidenceItem | null>(evidence[0] || null);

  const getStatusBadge = (status: EvidenceItem['evidenceStatus']) => {
    switch (status) {
      case 'STORED_LOCALLY':
        return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30';
      case 'TRANSMITTED':
        return 'bg-cyan-500/10 text-cyan-400 border-cyan-500/30';
      case 'PENDING':
        return 'bg-amber-500/10 text-amber-400 border-amber-500/30';
      default:
        return 'bg-slate-700 text-slate-300 border-slate-600';
    }
  };

  const getTransmissionBadge = (status: EvidenceItem['transmissionStatus']) => {
    switch (status) {
      case 'HELD_SILENT':
        return 'bg-slate-800 text-slate-300 border-slate-700';
      case 'COMPLETED':
        return 'bg-cyan-500/20 text-cyan-400 border-cyan-500/40';
      case 'QUEUED_FOR_RTH':
        return 'bg-amber-500/20 text-amber-400 border-amber-500/40';
      default:
        return 'bg-slate-800 text-slate-400 border-slate-700';
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header Card */}
      <div className="bg-[#0b1019] rounded-xl p-6 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-purple-400 uppercase tracking-widest font-semibold mb-1">
            <FolderLock className="w-4 h-4" />
            <span>Secure Evidence Repository</span>
          </div>
          <h2 className="text-2xl font-bold font-mono text-slate-100 tracking-tight">
            ONBOARD EVIDENCE RETENTION VAULT
          </h2>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl font-sans">
            Edge AI evidence snapshots and sensor bursts buffered on UAV NVMe solid-state storage. Transmitted only upon explicit Mission Card criteria or ground recovery.
          </p>
        </div>

        <div className="flex items-center gap-3 font-mono text-xs">
          <div className="p-2.5 rounded bg-[#0d1422] border border-slate-800 text-right">
            <span className="text-[10px] text-slate-400 block uppercase">EVIDENCE POLICY</span>
            <span className="font-bold text-purple-400">{mission.card.evidence}</span>
          </div>
          <div className="p-2.5 rounded bg-[#0d1422] border border-slate-800 text-right">
            <span className="text-[10px] text-slate-400 block uppercase">RECORDS STORED</span>
            <span className="font-bold text-cyan-400">{evidence.length} ITEMS</span>
          </div>
        </div>
      </div>

      {/* Main Evidence Registry & Inspection Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 font-mono">
        {/* Evidence Table */}
        <div className="lg:col-span-2 bg-[#0b1019] rounded-xl p-5 border border-slate-800 overflow-hidden">
          <div className="flex items-center justify-between pb-3 mb-3 border-b border-slate-800 text-xs">
            <span className="text-slate-400 uppercase tracking-wider font-bold">
              Evidence Events Register
            </span>
            <span className="text-[10px] text-slate-400">EDGE STORAGE PARTITION: /dev/nvme0n1</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 text-[11px]">
                  <th className="pb-2.5">ID / TIME</th>
                  <th className="pb-2.5">DETECTION</th>
                  <th className="pb-2.5">LOCATION</th>
                  <th className="pb-2.5">EVIDENCE STATUS</th>
                  <th className="pb-2.5">LOCAL RETENTION</th>
                  <th className="pb-2.5 text-right">TRANSMISSION</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {evidence.map((item) => (
                  <tr
                    key={item.id}
                    onClick={() => setSelectedItem(item)}
                    className={`cursor-pointer transition-colors ${
                      selectedItem?.id === item.id
                        ? 'bg-cyan-950/30 text-cyan-300'
                        : 'hover:bg-slate-800/30 text-slate-300'
                    }`}
                  >
                    <td className="py-3">
                      <div className="font-bold text-slate-200">{item.id}</div>
                      <div className="text-[10px] text-slate-400">{item.timestamp}</div>
                    </td>
                    <td className="py-3 font-semibold">
                      <span>{item.detection}</span>
                      <span className="text-[10px] text-slate-400 block">{item.confidence}% Conf</span>
                    </td>
                    <td className="py-3 text-slate-400 truncate max-w-xs">{item.location}</td>
                    <td className="py-3">
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded border uppercase font-bold ${getStatusBadge(
                          item.evidenceStatus
                        )}`}
                      >
                        {item.evidenceStatus}
                      </span>
                    </td>
                    <td className="py-3 text-[11px] text-slate-400">
                      {item.localRetentionStatus}
                    </td>
                    <td className="py-3 text-right">
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded border uppercase font-bold ${getTransmissionBadge(
                          item.transmissionStatus
                        )}`}
                      >
                        {item.transmissionStatus}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Selected Evidence Item Detail Card */}
        <div className="bg-[#0b1019] rounded-xl p-5 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <span className="text-xs text-slate-400 uppercase tracking-wider font-bold flex items-center gap-2">
              <Crosshair className="w-4 h-4 text-purple-400" />
              Evidence Inspector
            </span>
            {selectedItem && (
              <span className="text-xs text-purple-400 font-bold">{selectedItem.id}</span>
            )}
          </div>

          {selectedItem ? (
            <div className="space-y-4 text-xs">
              {/* Synthetic Thermal / EO Frame Reticle Preview */}
              <div className="relative w-full h-44 rounded-lg bg-[#060a12] border border-slate-800 overflow-hidden flex flex-col justify-between p-3">
                <div className="flex justify-between items-center text-[10px] text-purple-300">
                  <span>REC_PAYLOAD: 1080p EO_FLIR</span>
                  <span>SIZE: {(selectedItem.fileSizeKb / 1024).toFixed(2)} MB</span>
                </div>

                <div className="flex flex-col items-center justify-center">
                  <div className="w-20 h-20 border border-dashed border-purple-400/70 rounded flex flex-col items-center justify-center bg-purple-950/20">
                    <span className="text-[10px] text-purple-200 font-bold uppercase">{selectedItem.detection}</span>
                    <span className="text-[9px] text-slate-400">{selectedItem.confidence}% CONF</span>
                  </div>
                </div>

                <div className="flex justify-between items-center text-[9px] text-slate-400">
                  <span>GEO: {selectedItem.coordinates.lat.toFixed(4)}°N, {Math.abs(selectedItem.coordinates.lng).toFixed(4)}°W</span>
                  <span className="text-emerald-400">NVMe VERIFIED</span>
                </div>
              </div>

              {/* Attributes breakdown */}
              <div className="space-y-2">
                <div className="p-2.5 rounded bg-[#0d1422] border border-slate-800">
                  <span className="text-slate-400 text-[10px] block uppercase">CAPTURE REASON</span>
                  <span className="text-slate-200 font-sans text-xs mt-0.5 block leading-relaxed">
                    {selectedItem.reason}
                  </span>
                </div>

                <div className="p-2.5 rounded bg-[#0d1422] border border-slate-800 flex justify-between">
                  <span className="text-slate-400">Local Retention:</span>
                  <span className="font-bold text-emerald-400">{selectedItem.localRetentionStatus}</span>
                </div>

                <div className="p-2.5 rounded bg-[#0d1422] border border-slate-800 flex justify-between">
                  <span className="text-slate-400">RF Emission Policy:</span>
                  <span className="font-bold text-amber-400">{selectedItem.transmissionStatus}</span>
                </div>
              </div>

              <div className="p-3 rounded bg-slate-900/80 border border-slate-800 text-[11px] text-slate-400 leading-relaxed font-sans">
                <strong className="text-slate-200">Stealth Assurance: </strong>
                Large image payloads remain stored locally on the UAV. Only when mission policy permits will compressed evidence be radiated over RF.
              </div>
            </div>
          ) : (
            <div className="text-center py-12 text-slate-400 text-xs">
              Select an evidence entry to view payload details
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
