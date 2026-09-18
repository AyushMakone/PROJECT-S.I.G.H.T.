import React, { useState } from 'react';
import { useSimulation } from '../../hooks/useSimulation';
import { MissionCardUploadModal } from './MissionCardUploadModal';
import {
  Upload,
  FileCheck2,
  Crosshair,
  Shield,
  Layers,
  Radio,
  Battery,
  Clock,
  CheckCircle2
} from 'lucide-react';

export const MissionCardView: React.FC = () => {
  const { mission, updateMissionCard } = useSimulation();
  const card = mission.card;
  const [isModalOpen, setIsModalOpen] = useState(false);

  return (
    <div className="space-y-6">
      {/* Top Header Card */}
      <div className="bg-[#0b1019] border border-slate-800 rounded-xl p-6 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-cyan-400 uppercase tracking-widest font-semibold mb-1">
            <FileCheck2 className="w-4 h-4" />
            <span>Active Mission Card Definition</span>
          </div>
          <h2 className="text-2xl font-bold text-slate-100 font-mono tracking-tight">
            {card.missionId} — {card.objective}
          </h2>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl font-sans">
            {card.description || 'Configures operational thresholds, target relevance, and RF link emission constraints.'}
          </p>
        </div>

        <button
          onClick={() => setIsModalOpen(true)}
          className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold font-mono text-xs transition-all shadow-lg shadow-cyan-500/20 shrink-0"
        >
          <Upload className="w-4 h-4" />
          UPLOAD MISSION CARD
        </button>
      </div>

      {/* Primary Mission Card Specs Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 font-mono">
        {/* Mission ID & UAV */}
        <div className="bg-[#0b1019] rounded-xl p-4 border border-slate-800">
          <div className="flex items-center gap-2 text-xs text-slate-400 uppercase tracking-wider mb-2">
            <Shield className="w-4 h-4 text-cyan-400" />
            <span>Mission ID</span>
          </div>
          <div className="text-xl font-bold text-slate-100">{card.missionId}</div>
          <div className="text-xs text-slate-400 mt-1">Platform: {card.uavId}</div>
        </div>

        {/* Objective */}
        <div className="bg-[#0b1019] rounded-xl p-4 border border-slate-800">
          <div className="flex items-center gap-2 text-xs text-slate-400 uppercase tracking-wider mb-2">
            <Crosshair className="w-4 h-4 text-cyan-400" />
            <span>Objective</span>
          </div>
          <div className="text-lg font-bold text-slate-100">{card.objective}</div>
          <div className="text-xs text-emerald-400 mt-1 flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" /> Flight in progress
          </div>
        </div>

        {/* Persistence */}
        <div className="bg-[#0b1019] rounded-xl p-4 border border-slate-800">
          <div className="flex items-center gap-2 text-xs text-slate-400 uppercase tracking-wider mb-2">
            <Clock className="w-4 h-4 text-amber-400" />
            <span>Persistence</span>
          </div>
          <div className="text-xl font-bold text-amber-400">{card.persistence}</div>
          <div className="text-xs text-slate-400 mt-1">
            Threshold: ≥ {card.persistenceFrames} consecutive frames
          </div>
        </div>

        {/* Battery/RTH */}
        <div className="bg-[#0b1019] rounded-xl p-4 border border-slate-800">
          <div className="flex items-center gap-2 text-xs text-slate-400 uppercase tracking-wider mb-2">
            <Battery className="w-4 h-4 text-red-400" />
            <span>Battery/RTH</span>
          </div>
          <div className="text-xl font-bold text-red-400">{card.batteryRthThreshold}</div>
          <div className="text-xs text-slate-400 mt-1">Auto-abort return threshold</div>
        </div>
      </div>

      {/* Target Relevance & RF Policy Breakdown */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 font-mono">
        {/* Relevant Objects */}
        <div className="bg-[#0b1019] rounded-xl p-5 border border-slate-800">
          <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-800">
            <span className="text-xs text-slate-400 uppercase tracking-wider font-bold flex items-center gap-2">
              <Layers className="w-4 h-4 text-cyan-400" />
              Relevant Objects Filter
            </span>
            <span className="text-[10px] text-slate-400">EDGE AI DETECTOR MAPPING</span>
          </div>

          <div className="flex flex-wrap gap-2 mb-4">
            {card.relevantObjects.map((obj) => (
              <div
                key={obj}
                className="px-3 py-1.5 rounded-lg bg-cyan-950/40 border border-cyan-500/40 text-cyan-300 font-bold text-sm flex items-center gap-1.5"
              >
                <span className="w-2 h-2 rounded-full bg-cyan-400" />
                {obj}
              </div>
            ))}
          </div>

          <p className="text-xs text-slate-400 font-sans leading-relaxed">
            All other objects detected by onboard perception (e.g. Animal, foliage, clutter) are automatically flagged as <strong className="text-slate-300">SUPPRESS</strong> at the edge with zero RF transmission.
          </p>
        </div>

        {/* Communication Policy & Evidence */}
        <div className="bg-[#0b1019] rounded-xl p-5 border border-slate-800">
          <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-800">
            <span className="text-xs text-slate-400 uppercase tracking-wider font-bold flex items-center gap-2">
              <Radio className="w-4 h-4 text-emerald-400" />
              Communication & Evidence Policy
            </span>
            <span className="text-[10px] text-slate-400">S.I.G.H.T. LINK CONTROLLER</span>
          </div>

          <div className="grid grid-cols-2 gap-3 mb-3">
            <div className="p-3 rounded bg-[#0d1422] border border-slate-800">
              <span className="text-[10px] text-slate-400 block uppercase">COMMUNICATION POLICY</span>
              <span className="text-base font-bold text-emerald-400">{card.communicationPolicy}</span>
            </div>
            <div className="p-3 rounded bg-[#0d1422] border border-slate-800">
              <span className="text-[10px] text-slate-400 block uppercase">EVIDENCE GATHERING</span>
              <span className={`text-base font-bold ${card.evidence === 'Enabled' ? 'text-purple-400' : 'text-slate-400'}`}>
                {card.evidence}
              </span>
            </div>
          </div>

          <p className="text-xs text-slate-400 font-sans leading-relaxed">
            Link remains in silent <strong className="text-slate-300">INACTIVE</strong> mode until a target satisfies priority zone geofence and persistence frames simultaneously.
          </p>
        </div>
      </div>

      {/* Priority Surveillance Zones */}
      <div className="bg-[#0b1019] rounded-xl p-5 border border-slate-800">
        <div className="flex items-center justify-between mb-3 pb-2 border-b border-slate-800 font-mono">
          <span className="text-xs text-slate-400 uppercase tracking-wider font-bold">
            Priority Geofenced Hot Zones ({card.priorityZones.length})
          </span>
          <span className="text-[10px] text-slate-400">SPATIAL CONTEXT GEOFENCES</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 font-mono">
          {card.priorityZones.map((zone, idx) => (
            <div
              key={zone}
              className="p-3.5 rounded-lg bg-[#0e1625] border border-slate-800 flex items-center justify-between"
            >
              <div className="flex items-center gap-3">
                <span className="w-6 h-6 rounded bg-red-500/20 text-red-400 border border-red-500/40 flex items-center justify-center text-xs font-bold">
                  {idx + 1}
                </span>
                <div>
                  <div className="text-sm font-bold text-slate-200">{zone}</div>
                  <div className="text-[11px] text-slate-400">Restricted operational envelope</div>
                </div>
              </div>
              <span className="text-[10px] font-semibold text-emerald-400 bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-800/40">
                ACTIVE
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Modal */}
      <MissionCardUploadModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onApply={updateMissionCard}
        currentCard={card}
      />
    </div>
  );
};
