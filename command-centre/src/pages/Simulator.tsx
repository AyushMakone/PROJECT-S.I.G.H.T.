import React, { useState } from 'react';
import { useSimulation } from '../hooks/useSimulation';
import { ThreeDViewer } from '../components/simulator/ThreeDViewer';
import { CameraFeed } from '../components/camera/CameraFeed';
import { StatusBadge } from '../components/common/StatusBadge';
import {
  Cpu,
  Pause,
  ArrowUp,
  ArrowDown,
  Home,
  ShieldCheck,
  ShieldAlert,
  Wifi,
  WifiOff,
  Crosshair,
  Compass,
  ChevronRight,
  Sliders,
  Radio,
  Activity
} from 'lucide-react';

export const Simulator: React.FC = () => {
  const {
    telemetry,
    governor,
    detections,
    priorityZones,
    connectionStatus,
    simulatorMode,
    lastTelemetryTimestamp,
    connectSimulator,
    disconnectSimulator,
    arm,
    disarm,
    takeoff,
    land,
    hover,
    move,
    setHeading,
    returnToHome
  } = useSimulation();

  const [selectedMode, setSelectedMode] = useState<'local' | 'cloud' | 'fallback'>(
    (simulatorMode === 'cloud' || simulatorMode === 'local' || simulatorMode === 'fallback')
      ? simulatorMode as 'cloud' | 'local' | 'fallback'
      : 'local'
  );
  const [takeoffAlt, setTakeoffAlt] = useState<number>(15.0);
  const [actionLog, setActionLog] = useState<string>('[SIM] Ready — connect to ArduPilot SITL (tcp:127.0.0.1:5760) or select mode.');
  const [isProcessing, setIsProcessing] = useState<boolean>(false);

  const handleConnect = async () => {
    setIsProcessing(true);
    setActionLog(`[SIM] Connecting to ${selectedMode.toUpperCase()} MAVLink simulator...`);
    try {
      const res = await connectSimulator(selectedMode);
      setActionLog(`[SIM] ${res.status}: Mode=${res.mode?.toUpperCase()} Connected=${res.isConnected}`);
    } catch (e: any) {
      setActionLog(`[SIM] Connect failed: ${e.message}`);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleDisconnect = async () => {
    setIsProcessing(true);
    try {
      await disconnectSimulator();
      setActionLog('[SIM] Simulator disconnected.');
    } finally {
      setIsProcessing(false);
    }
  };

  const handleArm = async () => {
    setIsProcessing(true);
    setActionLog('[SIM] → ARM command (MAV_CMD_COMPONENT_ARM_DISARM)...');
    const res = await arm();
    setActionLog(`[SIM] ARM: ${res.status}`);
    setIsProcessing(false);
  };

  const handleDisarm = async () => {
    setIsProcessing(true);
    setActionLog('[SIM] → DISARM command...');
    const res = await disarm();
    setActionLog(`[SIM] DISARM: ${res.status}`);
    setIsProcessing(false);
  };

  const handleTakeoff = async () => {
    setIsProcessing(true);
    setActionLog(`[SIM] → TAKEOFF ${takeoffAlt}m (MAV_CMD_NAV_TAKEOFF)...`);
    const res = await takeoff(takeoffAlt);
    setActionLog(`[SIM] TAKEOFF: ${res.status}`);
    setIsProcessing(false);
  };

  const handleLand = async () => {
    setIsProcessing(true);
    setActionLog('[SIM] → LAND command (MAV_CMD_NAV_LAND)...');
    const res = await land();
    setActionLog(`[SIM] LAND: ${res.status}`);
    setIsProcessing(false);
  };

  const handleHover = async () => {
    setIsProcessing(true);
    setActionLog('[SIM] → HOVER / LOITER hold position...');
    const res = await hover();
    setActionLog(`[SIM] HOVER: ${res.status}`);
    setIsProcessing(false);
  };

  const handleMove = async (vx: number, vy: number, vz: number, yaw: number = 0) => {
    setActionLog(`[SIM] → MOVE vx=${vx} vy=${vy} vz=${vz} (SET_POSITION_TARGET_LOCAL_NED)`);
    await move(vx, vy, vz, yaw);
  };

  const handleSetHeading = async (hdg: number) => {
    setActionLog(`[SIM] → HEADING ${hdg}° (MAV_CMD_CONDITION_YAW)`);
    const res = await setHeading(hdg);
    setActionLog(`[SIM] HEADING: ${res.status}`);
  };

  const handleRth = async () => {
    setIsProcessing(true);
    setActionLog('[SIM] → RETURN TO HOME (MAV_CMD_NAV_RETURN_TO_LAUNCH)...');
    const res = await returnToHome();
    setActionLog(`[SIM] RTH: ${res.status}`);
    setIsProcessing(false);
  };

  const isOnline = connectionStatus === 'TELEMETRY ACTIVE' || connectionStatus === 'CONNECTED';
  const isConnecting = connectionStatus === 'CONNECTING';

  const getStatusVariant = () => {
    if (isOnline) return 'emerald';
    if (isConnecting) return 'amber';
    if (connectionStatus.includes('LOST')) return 'red';
    return 'slate';
  };

  const getModeLabel = (mode: string) => {
    switch (mode) {
      case 'local':    return 'ArduPilot SITL (TCP:5760)';
      case 'cloud':    return 'Cloud PX4 SITL (UDP:14550)';
      case 'fallback': return 'Fallback Fixture (Dev Only)';
      default:         return 'UNKNOWN';
    }
  };

  const getModeColor = (mode: string) => {
    switch (mode) {
      case 'local':    return 'text-purple-400';
      case 'cloud':    return 'text-blue-400';
      default:         return 'text-amber-400';
    }
  };

  return (
    <div className="p-6 max-w-[1800px] mx-auto w-full space-y-6 font-mono">

      {/* ── Header ──────────────────────────────────────────── */}
      <div className="bg-[#0b1019] rounded-xl p-6 border border-slate-800 flex flex-col lg:flex-row lg:items-center justify-between gap-4 shadow-xl">
        <div>
          <div className="flex items-center gap-2 text-xs text-cyan-400 uppercase tracking-widest font-semibold mb-1">
            <Cpu className="w-4 h-4" />
            <span>S.I.G.H.T. — Genuine UAV Simulator Interface (MAVLink 2.0)</span>
          </div>
          <h2 className="text-2xl font-bold text-slate-100 tracking-tight">
            ARDUPILOT / PX4 SITL FLIGHT CONSOLE
          </h2>
          <p className="text-xs text-slate-400 mt-1 max-w-3xl font-sans">
            Source of truth:{' '}
            <span className="text-cyan-400 font-semibold">ArduPilot / PX4 SITL</span> —
            6-DOF EKF3 multi-rotor aerodynamics, real sensor simulation, MAVLink 2.0 telemetry &amp; command dispatch.
            Zero synthetic flight math or client-side interpolation.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="px-3 py-1.5 rounded bg-[#0d1422] border border-slate-800 text-xs">
            <span className="text-[10px] text-slate-500 block uppercase">Active Mode</span>
            <span className={`font-bold ${getModeColor(simulatorMode)}`}>
              {getModeLabel(simulatorMode)}
            </span>
          </div>
          <StatusBadge
            label={connectionStatus}
            variant={getStatusVariant()}
            pulse={isOnline}
            size="md"
          />
        </div>
      </div>

      {/* ── Mode Selector & Connect Bar ─────────────────────── */}
      <div className="bg-[#0b1019] rounded-xl p-4 border border-slate-800 flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs text-slate-400 font-bold uppercase mr-1">Simulator Engine:</span>

          {/* Local ArduPilot / PX4 SITL */}
          <button
            id="sim-mode-local"
            onClick={() => setSelectedMode('local')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${
              selectedMode === 'local'
                ? 'bg-purple-500/20 text-purple-300 border border-purple-500/40 shadow-sm'
                : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
            }`}
          >
            ⬡ Local SITL (MAVLink TCP:5760)
          </button>

          {/* Cloud PX4 SITL */}
          <button
            id="sim-mode-cloud"
            onClick={() => setSelectedMode('cloud')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${
              selectedMode === 'cloud'
                ? 'bg-blue-500/20 text-blue-300 border border-blue-500/40'
                : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
            }`}
          >
            ☁ Cloud SITL (UDP:14550)
          </button>

          {/* Fallback (offline dev) */}
          <button
            id="sim-mode-fallback"
            onClick={() => setSelectedMode('fallback')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-colors ${
              selectedMode === 'fallback'
                ? 'bg-amber-500/20 text-amber-300 border border-amber-500/40'
                : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
            }`}
          >
            ⚠ Fallback (Offline Dev)
          </button>

          {/* Protocol info pill */}
          <div className="flex items-center gap-1 px-2 py-1 rounded text-[10px] text-cyan-400 border border-cyan-800 bg-cyan-900/10">
            <Radio className="w-3 h-3" />
            MAVLink 2.0
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            id="sim-connect-btn"
            onClick={handleConnect}
            disabled={isProcessing}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-slate-900 font-bold text-xs transition-colors shadow-lg disabled:opacity-50"
          >
            <Wifi className="w-4 h-4" />
            Connect
          </button>
          <button
            id="sim-disconnect-btn"
            onClick={handleDisconnect}
            disabled={isProcessing}
            className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs border border-slate-700 transition-colors"
          >
            <WifiOff className="w-4 h-4" />
            Disconnect
          </button>
        </div>
      </div>

      {/* ── Primary Viewports Grid ──────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* 3D Tactical Viewer */}
        <div className="lg:col-span-7 space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="uppercase font-bold tracking-wider flex items-center gap-2">
              <Compass className="w-4 h-4 text-cyan-400" />
              Real-Time 3D UAV Position (MAVLink EKF3 Telemetry)
            </span>
            <span className={isOnline ? 'text-emerald-400' : 'text-amber-400'}>
              {isOnline ? '◉ LIVE SITL' : '○ WAITING FOR SITL HEARTBEAT'}
            </span>
          </div>
          <ThreeDViewer
            telemetry={telemetry}
            priorityZones={priorityZones}
            onManualControl={handleMove}
            height="460px"
          />
        </div>

        {/* Live Camera + AI */}
        <div className="lg:col-span-5 space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="uppercase font-bold tracking-wider flex items-center gap-2">
              <Crosshair className="w-4 h-4 text-cyan-400" />
              Simulator Camera Frame + Edge AI
            </span>
            <span className="text-emerald-400">YOLO PIPELINE</span>
          </div>
          <CameraFeed
            telemetry={telemetry}
            detections={detections}
            governor={governor}
            height="460px"
          />
        </div>
      </div>

      {/* ── Flight Control Deck ─────────────────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Controls */}
        <div className="lg:col-span-2 bg-[#0b1019] rounded-xl p-5 border border-slate-800 space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3 text-xs">
            <span className="font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
              <Sliders className="w-4 h-4 text-cyan-400" />
              MAVLink Flight Control Deck
            </span>
            <span className="text-[11px] text-cyan-400 font-bold">
              AUTOPILOT: {telemetry.flightMode || 'DISARMED'}
              {telemetry.isArmed ? ' · ARMED' : ' · DISARMED'}
            </span>
          </div>

          <div className="flex flex-wrap items-center gap-3">
            {/* Arm / Disarm */}
            {!telemetry.isArmed ? (
              <button
                id="flight-arm-btn"
                onClick={handleArm}
                disabled={isProcessing}
                className="px-4 py-2 rounded-lg bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 border border-emerald-500/40 text-xs font-bold transition-colors flex items-center gap-2"
              >
                <ShieldCheck className="w-4 h-4" /> ARM UAV
              </button>
            ) : (
              <button
                id="flight-disarm-btn"
                onClick={handleDisarm}
                disabled={isProcessing}
                className="px-4 py-2 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-red-400 border border-red-500/40 text-xs font-bold transition-colors flex items-center gap-2"
              >
                <ShieldAlert className="w-4 h-4" /> DISARM
              </button>
            )}

            {/* Takeoff */}
            <div className="flex items-center gap-1 bg-slate-900 rounded-lg p-1 border border-slate-800">
              <select
                id="takeoff-alt-select"
                value={takeoffAlt}
                onChange={(e) => setTakeoffAlt(Number(e.target.value))}
                className="bg-transparent text-xs text-slate-200 px-2 py-1 outline-none"
              >
                <option value={5}>5m</option>
                <option value={10}>10m</option>
                <option value={15}>15m</option>
                <option value={25}>25m</option>
                <option value={50}>50m</option>
                <option value={84}>84m (Perimeter)</option>
              </select>
              <button
                id="flight-takeoff-btn"
                onClick={handleTakeoff}
                disabled={isProcessing}
                className="px-3 py-1.5 rounded bg-cyan-600 hover:bg-cyan-500 text-slate-900 font-bold text-xs transition-colors flex items-center gap-1.5"
              >
                <ArrowUp className="w-3.5 h-3.5" /> Takeoff
              </button>
            </div>

            {/* Hover */}
            <button
              id="flight-hover-btn"
              onClick={handleHover}
              disabled={isProcessing}
              className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs border border-slate-700 transition-colors flex items-center gap-1.5"
            >
              <Pause className="w-3.5 h-3.5" /> Hover / Loiter
            </button>

            {/* Land */}
            <button
              id="flight-land-btn"
              onClick={handleLand}
              disabled={isProcessing}
              className="px-4 py-2 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-400 border border-amber-500/40 text-xs font-bold transition-colors flex items-center gap-1.5"
            >
              <ArrowDown className="w-3.5 h-3.5" /> Land
            </button>

            {/* RTH */}
            <button
              id="flight-rth-btn"
              onClick={handleRth}
              disabled={isProcessing}
              className="px-4 py-2 rounded-lg bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 border border-purple-500/40 text-xs font-bold transition-colors flex items-center gap-1.5"
            >
              <Home className="w-3.5 h-3.5" /> Return To Home
            </button>
          </div>

          {/* Heading Presets */}
          <div className="space-y-1.5 pt-2">
            <span className="text-[11px] text-slate-400 uppercase font-bold block">
              Align Heading (MAV_CMD_CONDITION_YAW):
            </span>
            <div className="flex items-center gap-2 flex-wrap">
              {[0, 45, 90, 135, 180, 225, 270, 315].map((deg) => (
                <button
                  key={deg}
                  id={`heading-btn-${deg}`}
                  onClick={() => handleSetHeading(deg)}
                  className={`px-2 py-1 rounded text-[11px] border transition-colors ${
                    Math.abs(Math.round(telemetry.headingDegrees) - deg) < 5
                      ? 'bg-cyan-500/20 text-cyan-400 border-cyan-500/40 font-bold'
                      : 'bg-slate-900 text-slate-400 hover:text-slate-200 border-slate-800'
                  }`}
                >
                  {deg}°
                </button>
              ))}
            </div>
          </div>

          {/* Action Log */}
          <div className="p-3 rounded-lg bg-[#060a12] border border-slate-800/80 text-xs text-cyan-300 flex items-center gap-2">
            <ChevronRight className="w-3.5 h-3.5 shrink-0 text-cyan-400" />
            <span className="font-mono">{actionLog}</span>
          </div>
        </div>

        {/* Live Telemetry Matrix */}
        <div className="bg-[#0b1019] rounded-xl p-5 border border-slate-800 space-y-3">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2 text-xs">
            <span className="font-bold text-slate-400 uppercase flex items-center gap-2">
              <Activity className="w-3.5 h-3.5 text-cyan-400" />
              Live SITL Telemetry
            </span>
            <span className={`text-[10px] font-bold ${isOnline ? 'text-emerald-400' : 'text-slate-500'}`}>
              {isOnline ? 'AUTHENTIC SENSOR DATA' : 'WAITING FOR SITL'}
            </span>
          </div>
          <div className="space-y-2 text-xs">
            {[
              { label: 'Autopilot', value: simulatorMode === 'local' ? 'ArduPilot SITL' : simulatorMode === 'cloud' ? 'PX4 SITL (Cloud)' : 'Fallback Fixture', color: 'text-cyan-400' },
              { label: 'Position', value: `${(telemetry.lat || 0).toFixed(5)}°, ${(telemetry.lng || 0).toFixed(5)}°` },
              { label: 'Altitude AGL', value: `${telemetry.altitude || 0} m`, color: 'text-cyan-400' },
              { label: 'Ground Speed', value: `${telemetry.speed || 0} m/s` },
              { label: 'Climb Rate', value: `${telemetry.climbRate > 0 ? '+' : ''}${telemetry.climbRate || 0} m/s` },
              { label: 'Heading', value: `${telemetry.heading || '0.0°'} (${telemetry.headingDegrees || 0}°)` },
              { label: 'Attitude R/P/Y', value: `${telemetry.roll || 0}° / ${telemetry.pitch || 0}° / ${telemetry.yaw || 0}°` },
              { label: 'Battery', value: telemetry.battery != null ? `${telemetry.battery}% (${telemetry.batteryVoltage}V)` : 'N/A', color: telemetry.battery != null && telemetry.battery < 25 ? 'text-red-400' : 'text-emerald-400' },
              { label: 'GPS', value: `${telemetry.gpsStatus || 'NO_FIX'} (${telemetry.gpsSatellites || 0} Sats)` },
              { label: 'Flight Mode', value: telemetry.flightMode || 'DISARMED', color: telemetry.isArmed ? 'text-emerald-400' : 'text-slate-400' },
              { label: 'Last Telemetry', value: lastTelemetryTimestamp || telemetry.timestamp || 'WAITING', color: 'text-slate-500' },
            ].map(({ label, value, color }) => (
              <div key={label} className="flex justify-between py-1 border-b border-slate-800/50">
                <span className="text-slate-400">{label}:</span>
                <span className={color || 'text-slate-200'}>{value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
