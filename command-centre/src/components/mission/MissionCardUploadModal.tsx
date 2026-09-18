import React, { useState } from 'react';
import { MissionCard } from '../../types';
import { ALTERNATE_MISSION_CARDS } from '../../mock/missionData';
import { Upload, X, Check, FileJson } from 'lucide-react';

interface MissionCardUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onApply: (card: MissionCard) => void;
  currentCard: MissionCard;
}

export const MissionCardUploadModal: React.FC<MissionCardUploadModalProps> = ({
  isOpen,
  onClose,
  onApply,
  currentCard
}) => {
  const [selectedPreset, setSelectedPreset] = useState<string>(currentCard.missionId);
  const [jsonText, setJsonText] = useState<string>(JSON.stringify(currentCard, null, 2));
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSelectPreset = (card: MissionCard) => {
    setSelectedPreset(card.missionId);
    setJsonText(JSON.stringify(card, null, 2));
    setError(null);
  };

  const handleJsonChange = (val: string) => {
    setJsonText(val);
    try {
      JSON.parse(val);
      setError(null);
    } catch (e: any) {
      setError('Invalid JSON syntax');
    }
  };

  const handleApply = () => {
    try {
      const parsed: MissionCard = JSON.parse(jsonText);
      if (!parsed.missionId || !parsed.objective) {
        setError('Missing required missionId or objective fields.');
        return;
      }
      onApply(parsed);
      onClose();
    } catch (e) {
      setError('Cannot parse JSON mission card.');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in">
      <div className="bg-[#0b1019] border border-slate-700 rounded-xl w-full max-w-2xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-slate-800 bg-[#080d15]">
          <div className="flex items-center gap-2">
            <Upload className="w-4 h-4 text-cyan-400" />
            <span className="font-mono text-sm font-bold text-slate-100 uppercase tracking-wider">
              Upload / Select Mission Card
            </span>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-slate-200 p-1 rounded hover:bg-slate-800 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Modal Content */}
        <div className="p-5 space-y-4 overflow-y-auto flex-1 font-mono text-xs">
          {/* Presets Selector */}
          <div>
            <label className="text-slate-400 uppercase tracking-wider text-[11px] block mb-2 font-bold">
              Select Preset Scenario:
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
              {ALTERNATE_MISSION_CARDS.map((card) => (
                <button
                  key={card.missionId}
                  onClick={() => handleSelectPreset(card)}
                  className={`p-2.5 rounded-lg border text-left transition-all ${
                    selectedPreset === card.missionId
                      ? 'bg-cyan-950/40 border-cyan-500/80 text-cyan-300'
                      : 'bg-slate-900/60 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-200'
                  }`}
                >
                  <div className="font-bold">{card.missionId}</div>
                  <div className="text-[10px] text-slate-400 mt-1 truncate">{card.objective}</div>
                </button>
              ))}
            </div>
          </div>

          {/* JSON Editor / Preview */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-slate-400 uppercase tracking-wider text-[11px] font-bold flex items-center gap-1.5">
                <FileJson className="w-3.5 h-3.5 text-cyan-400" />
                Mission Card JSON Payload:
              </label>
              <span className="text-[10px] text-slate-400">Directly editable</span>
            </div>
            <textarea
              value={jsonText}
              onChange={(e) => handleJsonChange(e.target.value)}
              rows={12}
              className="w-full bg-[#070a10] border border-slate-800 rounded-lg p-3 text-cyan-300 font-mono text-xs focus:outline-none focus:border-cyan-500/80 resize-none"
              spellCheck={false}
            />
            {error && <div className="text-red-400 text-xs mt-1 font-mono">{error}</div>}
          </div>
        </div>

        {/* Modal Footer */}
        <div className="flex items-center justify-between px-5 py-3.5 border-t border-slate-800 bg-[#080d15]">
          <span className="text-[11px] text-slate-400 font-mono">
            Modifies active S.I.G.H.T. Mission state in real time
          </span>
          <div className="flex items-center gap-2 font-mono">
            <button
              onClick={onClose}
              className="px-3 py-1.5 rounded border border-slate-700 text-slate-300 hover:bg-slate-800 text-xs transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleApply}
              disabled={!!error}
              className="flex items-center gap-1.5 px-4 py-1.5 rounded bg-cyan-500 text-slate-950 font-bold hover:bg-cyan-400 disabled:opacity-50 text-xs transition-colors shadow-md shadow-cyan-500/20"
            >
              <Check className="w-3.5 h-3.5" />
              Apply Mission Card
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
