import React, { useState } from 'react';
import { Settings as SettingsIcon, Server, Volume2, Check } from 'lucide-react';

export const Settings: React.FC = () => {
  const [apiUrl, setApiUrl] = useState<string>('http://127.0.0.1:8000/api/v1');
  const [wsUrl, setWsUrl] = useState<string>('ws://127.0.0.1:8000/ws/mission');
  const [audioAlerts, setAudioAlerts] = useState<boolean>(true);
  const [savedNotice, setSavedNotice] = useState<boolean>(false);

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    setSavedNotice(true);
    setTimeout(() => setSavedNotice(false), 2500);
  };

  return (
    <div className="p-6 max-w-[1200px] mx-auto w-full space-y-6 font-mono">
      {/* Header */}
      <div className="bg-[#0b1019] rounded-xl p-6 border border-slate-800 flex items-center justify-between">
        <div>
          <div className="flex items-center gap-2 text-xs text-cyan-400 uppercase tracking-widest font-semibold mb-1">
            <SettingsIcon className="w-4 h-4" />
            <span>Station Configuration</span>
          </div>
          <h2 className="text-2xl font-bold text-slate-100 tracking-tight">
            GROUND COMMAND CENTRE SETTINGS
          </h2>
          <p className="text-xs text-slate-400 mt-1 font-sans">
            Adjust operator preferences, alert parameters, and future backend integration endpoints.
          </p>
        </div>
      </div>

      <form onSubmit={handleSave} className="space-y-6">
        {/* Future Backend Integration Endpoints */}
        <div className="bg-[#0b1019] rounded-xl p-5 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <span className="text-xs text-slate-400 uppercase tracking-wider font-bold flex items-center gap-2">
              <Server className="w-4 h-4 text-cyan-400" />
              Backend Network Endpoints (FastAPI Integration)
            </span>
            <span className="text-[10px] text-cyan-400">READY FOR FASTAPI</span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
            <div>
              <label className="text-slate-400 block mb-1">REST API BASE URL:</label>
              <input
                type="text"
                value={apiUrl}
                onChange={(e) => setApiUrl(e.target.value)}
                className="w-full bg-[#080d15] border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
              />
              <span className="text-[10px] text-slate-400 mt-1 block font-sans">
                Location of S.I.G.H.T. Python backend service.
              </span>
            </div>

            <div>
              <label className="text-slate-400 block mb-1">WEBSOCKET TELEMETRY STREAM:</label>
              <input
                type="text"
                value={wsUrl}
                onChange={(e) => setWsUrl(e.target.value)}
                className="w-full bg-[#080d15] border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-cyan-500 font-mono"
              />
              <span className="text-[10px] text-slate-400 mt-1 block font-sans">
                Real-time duplex socket for telemetry & Governor events.
              </span>
            </div>
          </div>
        </div>

        {/* Operational Preferences */}
        <div className="bg-[#0b1019] rounded-xl p-5 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800">
            <span className="text-xs text-slate-400 uppercase tracking-wider font-bold flex items-center gap-2">
              <Volume2 className="w-4 h-4 text-amber-400" />
              Alerts & Notifications
            </span>
          </div>

          <div className="flex items-center justify-between text-xs py-1">
            <div>
              <div className="font-bold text-slate-200">Governor Event Chime</div>
              <div className="text-slate-400 font-sans text-[11px]">
                Play tactical sound tone when Governor transitions to EVENT or EVIDENCE
              </div>
            </div>
            <button
              type="button"
              onClick={() => setAudioAlerts(!audioAlerts)}
              className={`w-11 h-6 rounded-full transition-colors relative ${
                audioAlerts ? 'bg-cyan-500' : 'bg-slate-800'
              }`}
            >
              <span
                className={`w-4 h-4 rounded-full bg-white absolute top-1 transition-transform ${
                  audioAlerts ? 'left-6' : 'left-1'
                }`}
              />
            </button>
          </div>
        </div>

        {/* Action Button */}
        <div className="flex items-center justify-between pt-2">
          {savedNotice ? (
            <span className="text-emerald-400 text-xs font-bold flex items-center gap-1.5">
              <Check className="w-4 h-4" /> Preferences saved successfully.
            </span>
          ) : (
            <div />
          )}

          <button
            type="submit"
            className="px-5 py-2.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-bold text-xs transition-colors shadow-lg shadow-cyan-500/20"
          >
            Save Configuration
          </button>
        </div>
      </form>
    </div>
  );
};
