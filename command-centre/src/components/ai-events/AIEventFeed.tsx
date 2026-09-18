import React, { useState } from 'react';
import { useSimulation } from '../../hooks/useSimulation';
import { AIEventCard } from './AIEventCard';
import { Detection } from '../../types';
import { Eye, Search, Filter, ShieldCheck, Crosshair } from 'lucide-react';

export const AIEventFeed: React.FC = () => {
  const { detections } = useSimulation();
  const [selectedTarget, setSelectedTarget] = useState<Detection | null>(detections[0] || null);
  const [filterObj, setFilterObj] = useState<string>('ALL');
  const [filterDecision, setFilterDecision] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const filteredDetections = detections.filter((det) => {
    if (filterObj !== 'ALL' && det.object !== filterObj) return false;
    if (filterDecision !== 'ALL' && det.governorDecision !== filterDecision) return false;
    if (
      searchQuery &&
      !det.locationName.toLowerCase().includes(searchQuery.toLowerCase()) &&
      !det.object.toLowerCase().includes(searchQuery.toLowerCase()) &&
      !det.id.toLowerCase().includes(searchQuery.toLowerCase())
    ) {
      return false;
    }
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Top Controls Bar */}
      <div className="bg-[#0b1019] rounded-xl p-4 border border-slate-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <Eye className="w-5 h-5 text-cyan-400" />
          <div>
            <h2 className="text-lg font-bold font-mono text-slate-100 tracking-tight">
              AI Perception & Detection Stream
            </h2>
            <div className="text-xs text-slate-400">
              Live inference log from UAV Edge-AI neural detector
            </div>
          </div>
        </div>

        {/* Filter Toolbar */}
        <div className="flex flex-wrap items-center gap-2 font-mono text-xs">
          {/* Search Box */}
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-400 absolute left-2.5 top-2.5" />
            <input
              type="text"
              placeholder="Search target/zone..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="bg-[#080d15] border border-slate-700/80 rounded-lg pl-8 pr-3 py-1.5 text-slate-200 placeholder-slate-400 text-xs focus:outline-none focus:border-cyan-500 w-44"
            />
          </div>

          {/* Object Filter */}
          <select
            value={filterObj}
            onChange={(e) => setFilterObj(e.target.value)}
            className="bg-[#080d15] border border-slate-700/80 rounded-lg px-2.5 py-1.5 text-slate-300 text-xs focus:outline-none focus:border-cyan-500"
          >
            <option value="ALL">All Objects</option>
            <option value="Vehicle">Vehicle</option>
            <option value="Person">Person</option>
            <option value="Animal">Animal</option>
          </select>

          {/* Decision Filter */}
          <select
            value={filterDecision}
            onChange={(e) => setFilterDecision(e.target.value)}
            className="bg-[#080d15] border border-slate-700/80 rounded-lg px-2.5 py-1.5 text-slate-300 text-xs focus:outline-none focus:border-cyan-500"
          >
            <option value="ALL">All Decisions</option>
            <option value="EVENT">EVENT</option>
            <option value="RETAIN">RETAIN</option>
            <option value="SUPPRESS">SUPPRESS</option>
            <option value="EVIDENCE">EVIDENCE</option>
          </select>
        </div>
      </div>

      {/* Main Events Grid + Target Inspect Drawer */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Event Cards List */}
        <div className="lg:col-span-2 space-y-3">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400 px-1">
            <span>SHOWING {filteredDetections.length} OF {detections.length} DETECTIONS</span>
            <span>CHRONOLOGICAL ORDER (NEWEST FIRST)</span>
          </div>

          <div className="space-y-3 overflow-y-auto max-h-[72vh] pr-1">
            {filteredDetections.map((det) => (
              <AIEventCard
                key={det.id}
                detection={det}
                isSelected={selectedTarget?.id === det.id}
                onSelect={(d) => setSelectedTarget(d)}
              />
            ))}

            {filteredDetections.length === 0 && (
              <div className="text-center py-12 bg-[#0b1019] rounded-xl border border-slate-800 text-slate-400 font-mono text-xs">
                NO DETECTIONS MATCHING SELECTED FILTERS
              </div>
            )}
          </div>
        </div>

        {/* Selected Target Tactical Inspection Panel */}
        <div className="bg-[#0b1019] rounded-xl p-5 border border-slate-800 h-fit space-y-4 font-mono">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <span className="text-xs text-slate-400 uppercase tracking-wider font-bold flex items-center gap-1.5">
              <Crosshair className="w-4 h-4 text-cyan-400" />
              Target Analysis
            </span>
            {selectedTarget && (
              <span className="text-xs text-cyan-400 font-bold">{selectedTarget.id}</span>
            )}
          </div>

          {selectedTarget ? (
            <div className="space-y-4 text-xs">
              {/* Mock Synthetic Bounding Box Reticle */}
              <div className="relative w-full h-44 rounded-lg bg-[#060a12] border border-slate-800 overflow-hidden flex items-center justify-center">
                {/* Crosshairs & grid */}
                <div className="absolute inset-0 bg-[radial-gradient(#1e293b_1px,transparent_1px)] [background-size:16px_16px] opacity-40" />
                <div className="absolute inset-x-0 top-1/2 h-px bg-cyan-500/20" />
                <div className="absolute inset-y-0 left-1/2 w-px bg-cyan-500/20" />

                {/* Target box */}
                <div className="relative w-28 h-28 border-2 border-cyan-400/80 rounded flex flex-col justify-between p-1.5 shadow-[0_0_15px_rgba(6,182,212,0.3)] bg-cyan-950/20">
                  <div className="flex justify-between items-center text-[10px] text-cyan-300 font-bold">
                    <span>{selectedTarget.object}</span>
                    <span>{selectedTarget.confidence}%</span>
                  </div>
                  <div className="text-center">
                    <span className="text-[9px] text-slate-300">P:{selectedTarget.persistence} frames</span>
                  </div>
                  <div className="text-[9px] text-slate-400 text-right">
                    EO/IR OPTICAL
                  </div>
                </div>

                <div className="absolute bottom-2 left-2 text-[10px] text-slate-400">
                  FRAME BUFFER: #{selectedTarget.id.replace('DET-', '')}
                </div>
              </div>

              {/* Data Specs */}
              <div className="space-y-2">
                <div className="flex justify-between p-2 rounded bg-[#0d1422] border border-slate-800">
                  <span className="text-slate-400">Classified Target:</span>
                  <span className="font-bold text-slate-100">{selectedTarget.object}</span>
                </div>
                <div className="flex justify-between p-2 rounded bg-[#0d1422] border border-slate-800">
                  <span className="text-slate-400">Detection Confidence:</span>
                  <span className="font-bold text-cyan-400">{selectedTarget.confidence}%</span>
                </div>
                <div className="flex justify-between p-2 rounded bg-[#0d1422] border border-slate-800">
                  <span className="text-slate-400">Temporal Persistence:</span>
                  <span className="font-bold text-slate-100">{selectedTarget.persistence} frames</span>
                </div>
                <div className="flex justify-between p-2 rounded bg-[#0d1422] border border-slate-800">
                  <span className="text-slate-400">Zone Classification:</span>
                  <span className={`font-bold ${selectedTarget.insidePriorityZone ? 'text-red-400' : 'text-slate-400'}`}>
                    {selectedTarget.zone}
                  </span>
                </div>
                <div className="flex justify-between p-2 rounded bg-[#0d1422] border border-slate-800">
                  <span className="text-slate-400">Governor Outcome:</span>
                  <span className="font-bold text-cyan-300">{selectedTarget.governorDecision}</span>
                </div>
              </div>

              {/* Governor Rationale note */}
              <div className="p-3 rounded bg-slate-900/80 border border-slate-800 text-[11px] text-slate-400 leading-relaxed font-sans">
                <strong className="text-slate-200">Governor Reasoning: </strong>
                {selectedTarget.governorDecision === 'EVENT'
                  ? 'Target object is in mission card, verified inside priority zone, and exceeds persistence threshold. Transmitted via ultra-compact RF metadata.'
                  : selectedTarget.governorDecision === 'RETAIN'
                  ? 'Target object matches mission relevance but is located outside priority hot zone. Retained in edge NVMe circular buffer.'
                  : 'Target object is not part of mission card priority objects. Discarded at edge perception layer.'}
              </div>
            </div>
          ) : (
            <div className="text-center py-12 text-slate-400 text-xs">
              Select a detection to inspect telemetry & frame data
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
