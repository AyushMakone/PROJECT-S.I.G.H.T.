import React, { useState, useEffect } from 'react';
import { Telemetry, Detection, GovernorDecision } from '../../types';
import { DetectorStatus } from '../../services/api';
import { CAMERA_STREAM_URL, CAMERA_FRAME_URL } from '../../services/api';
import { Video, Camera, Crosshair, AlertCircle, RefreshCw } from 'lucide-react';

interface CameraFeedProps {
  telemetry: Telemetry;
  detections?: Detection[];
  governor?: GovernorDecision;
  detectorStatus?: DetectorStatus | null;
  cameraStatus?: { online?: boolean; status?: string; fps?: number | null; resolution?: string | null } | null;
  className?: string;
  height?: string;
}

export const CameraFeed: React.FC<CameraFeedProps> = ({
  telemetry,
  detections = [],
  governor,
  detectorStatus,
  cameraStatus,
  className = '',
  height = '360px'
}) => {
  const [streamError, setStreamError] = useState<boolean>(false);
  const [streamConnected, setStreamConnected] = useState<boolean>(false);
  const [useSnapshotMode, setUseSnapshotMode] = useState<boolean>(false);
  const [snapshotUrl, setSnapshotUrl] = useState<string>(CAMERA_FRAME_URL);
  const [fps, setFps] = useState<number>(10);

  // Snapshot polling mode fallback
  useEffect(() => {
    if (!useSnapshotMode) return;
    const interval = setInterval(() => {
      setSnapshotUrl(`${CAMERA_FRAME_URL}?t=${Date.now()}`);
    }, 1000 / fps);
    return () => clearInterval(interval);
  }, [useSnapshotMode, fps]);

  return (
    <div className={`relative w-full rounded-xl overflow-hidden border border-slate-800 bg-[#06090f] font-mono text-xs ${className}`}>
      {/* Top HUD Banner */}
      <div className="absolute top-2 left-2 right-2 flex items-center justify-between z-10 pointer-events-none">
        <div className="flex items-center gap-2 bg-[#090e18]/85 backdrop-blur-md px-2.5 py-1 rounded border border-slate-800 pointer-events-auto">
          <Camera className="w-3.5 h-3.5 text-cyan-400" />
          <span className="font-bold text-slate-200">OPTICAL GIMBAL EO SENSOR</span>
          <span className="text-slate-600">|</span>
          <span className="text-cyan-400">{telemetry.hasTelemetry ? `${telemetry.relativeAltitude ?? 'N/A'}m AGL` : '--- AGL'}</span>
          <span className="text-slate-600">|</span>
          <span className="text-slate-400">{telemetry.hasTelemetry ? `${telemetry.heading} (${telemetry.headingDegrees}°)` : 'UNKNOWN'}</span>
        </div>

        <div className="flex items-center gap-2 bg-[#090e18]/85 backdrop-blur-md px-2 py-1 rounded border border-slate-800 pointer-events-auto text-[11px]">
          <span className="text-slate-400">RES: {cameraStatus?.resolution ?? 'N/A'}</span>
          <span className="text-slate-600">|</span>
          <span className={detectorStatus?.runtime === 'READY' ? 'text-cyan-400' : 'text-amber-400'}>
            DETECTOR: {detectorStatus?.activeDetector?.toUpperCase() ?? 'UNAVAILABLE'}
          </span>
          <span className="text-slate-600">|</span>
          <button
            onClick={() => setUseSnapshotMode(!useSnapshotMode)}
            className="text-cyan-400 hover:text-cyan-300 transition-colors"
          >
            {useSnapshotMode ? 'MODE: POLLING' : 'MODE: STREAM'}
          </button>
        </div>
      </div>

      {/* Main Video Viewport */}
      <div style={{ height }} className="relative w-full flex items-center justify-center bg-slate-950 overflow-hidden">
        {!streamError ? (
          <img
            src={useSnapshotMode ? snapshotUrl : CAMERA_STREAM_URL}
            alt="UAV Camera Feed"
            className="w-full h-full object-cover"
            onError={() => {
              setStreamConnected(false);
              if (!useSnapshotMode) {
                setUseSnapshotMode(true);
              } else {
                setStreamError(true);
              }
            }}
            onLoad={() => { setStreamError(false); setStreamConnected(true); }}
          />
        ) : (
          <div className="flex flex-col items-center gap-2 text-slate-500 p-6 text-center">
            <Video className="w-8 h-8 text-slate-600" />
            <span className="text-slate-300 font-bold">OPTICAL STREAM STANDBY</span>
            <span className="text-[11px] text-slate-500 max-w-sm">
              No connected camera source. Gazebo/RTSP camera integration is not connected.
            </span>
            <button
              onClick={() => {
                setStreamError(false);
                setUseSnapshotMode(false);
              }}
              className="mt-2 flex items-center gap-1.5 px-3 py-1 rounded bg-slate-800 text-slate-300 hover:bg-slate-700 text-[11px] transition-colors"
            >
              <RefreshCw className="w-3 h-3" /> Retry Stream Connection
            </button>
          </div>
        )}

        {/* Center Tactical Reticle Crosshairs */}
        <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
          <div className="relative w-12 h-12 border border-cyan-400/40 rounded-full flex items-center justify-center">
            <div className="w-2 h-0.5 bg-cyan-400/80" />
            <div className="w-0.5 h-2 bg-cyan-400/80" />
            <Crosshair className="absolute w-4 h-4 text-cyan-400/60" />
          </div>
        </div>

        {/* Live Bounding Boxes & Governor Badges */}
        {detections.map((det) => {
          const [cx, cy, w, h] = det.normBbox || [0.5, 0.5, 0.1, 0.1];
          const left = `${Math.max(0, (cx - w / 2) * 100)}%`;
          const top = `${Math.max(0, (cy - h / 2) * 100)}%`;
          const width = `${Math.min(100, w * 100)}%`;
          const heightBox = `${Math.min(100, h * 100)}%`;

          const isEvent = governor?.decision === 'EVENT';
          const isRetain = governor?.decision === 'RETAIN';

          return (
            <div
              key={det.id}
              style={{ left, top, width, height: heightBox }}
              className={`absolute border-2 pointer-events-none transition-all ${
                isEvent
                  ? 'border-cyan-400 bg-cyan-500/10 shadow-[0_0_12px_rgba(0,243,255,0.4)]'
                  : isRetain
                  ? 'border-amber-400 bg-amber-500/10'
                  : 'border-slate-500 bg-slate-500/10'
              }`}
            >
              <div className="absolute -top-5 left-0 flex items-center gap-1 bg-[#090e18]/90 px-1.5 py-0.5 rounded text-[10px] font-bold text-slate-100 whitespace-nowrap">
                <span>{det.objectClass}</span>
                <span className="text-slate-300">T{det.trackId ?? 'N/A'}</span>
                <span className="text-cyan-400">{det.confidence}%</span>
                {governor && (
                  <span
                    className={`px-1 rounded text-[9px] ${
                      isEvent
                        ? 'bg-cyan-500/30 text-cyan-300'
                        : isRetain
                        ? 'bg-amber-500/30 text-amber-300'
                        : 'bg-slate-700 text-slate-300'
                    }`}
                  >
                    {governor.decision}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Bottom HUD Banner */}
      <div className="absolute bottom-2 left-2 right-2 flex items-center justify-between z-10 pointer-events-none">
        <div className="bg-[#090e18]/85 backdrop-blur-md px-2.5 py-1 rounded border border-slate-800 text-[11px] text-slate-400">
          CAMERA: <strong className={cameraStatus?.online ? 'text-cyan-400' : 'text-slate-400'}>{cameraStatus?.status ?? (streamConnected ? 'CONNECTED' : 'UNAVAILABLE')}</strong> | EDGE AI: <strong className="text-slate-400">{detectorStatus?.activeDetector?.toUpperCase() ?? 'UNAVAILABLE'}</strong> | TARGETS: <strong className="text-slate-200">{detections.length}</strong>
        </div>

        {governor && (
          <div className="bg-[#090e18]/85 backdrop-blur-md px-2.5 py-1 rounded border border-slate-800 text-[11px] flex items-center gap-2">
            <span className="text-slate-400">GOVERNOR:</span>
            <span
              className={`font-bold ${
                governor.decision === 'EVENT'
                  ? 'text-cyan-400'
                  : governor.decision === 'RETAIN'
                  ? 'text-amber-400'
                  : governor.decision === 'EVIDENCE'
                  ? 'text-purple-400'
                  : 'text-slate-400'
              }`}
            >
              {governor.decision}
            </span>
          </div>
        )}
      </div>
    </div>
  );
};
