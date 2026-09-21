export const API_BASE_URL = (import.meta as any).env?.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';

export interface BackendHealthResponse {
  status: string;
  version: string;
  components: Record<string, string>;
  uptime_s: number;
}

export interface RuntimeStatus {
  runtime?: string | null;
  connection_state?: string | null;
  heartbeat_received?: boolean;
  connected?: boolean;
  connection?: string | null;
  system_id?: number | null;
  component_id?: number | null;
  autopilot?: string | null;
  vehicle?: string | null;
  armed?: boolean | null;
  mode?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  altitude?: number | null;
  relative_altitude?: number | null;
  ground_speed?: number | null;
  heading?: number | null;
  roll?: number | null;
  pitch?: number | null;
  yaw?: number | null;
  battery?: number | null;
  gps_fix?: string | null;
  satellites?: number | null;
  timestamp?: string | null;
}

export interface CameraStatus {
  online?: boolean;
  status?: string;
  fps?: number | null;
  fov?: number | null;
  resolution?: string | null;
}

export interface DetectorStatus {
  configuredDetector?: string;
  activeDetector?: string;
  fallback?: boolean;
  reason?: string;
  modelPath?: string | null;
  modelFound?: boolean | null;
  modelLoaded?: boolean;
  runtime?: string;
  device?: string | null;
  lastFrameId?: number;
  detections?: number;
  activeTracks?: number;
  expiredTracks?: number;
}

export interface BackendDetection {
  id: string;
  objectClass: string;
  confidence: number;
  normBbox: [number, number, number, number];
  trackId: number;
  persistence: number;
  lat: number;
  lng: number;
  altitudeM: number;
  timestamp: string;
  frameId: number;
  source: string;
  governorDecision?: 'SUPPRESS' | 'RETAIN' | 'EVENT' | 'EVIDENCE';
  governorReason?: string;
  insidePriorityZone?: boolean;
  locationSource?: string;
  targetGeolocationAvailable?: boolean;
  zoneName?: string | null;
}

export interface BackendMissionZone {
  id: string;
  name: string;
  polygon: [number, number][];
  description?: string;
  priority?: 'HIGH' | 'MEDIUM' | 'LOW';
  active?: boolean;
}

export interface BackendMissionWaypoint {
  id: string;
  name?: string;
  lat: number;
  lon: number;
  altitude?: number;
  acceptanceRadius?: number;
}

export interface BackendMissionCard {
  missionId?: string;
  objective?: string;
  uavId?: string;
  relevantObjects?: string[];
  persistence?: string;
  persistenceFrames?: number;
  priorityZones?: BackendMissionZone[];
  waypoints?: BackendMissionWaypoint[];
  evidence?: string;
  communicationPolicy?: string;
  batteryRthThreshold?: string;
  batteryRthPercent?: number;
  minConfidencePercent?: number;
  description?: string;
}

export interface MissionWriteResponse {
  status: string;
  mission_id: string;
  message: string;
}

export class ApiRequestError extends Error {
  readonly status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiRequestError';
    this.status = status;
  }
}

function formatApiDetail(detail: unknown, fallback: string): string {
  if (typeof detail === 'string' && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const messages = detail.map((item) => {
      if (!item || typeof item !== 'object') return null;
      const record = item as { loc?: unknown[]; msg?: unknown };
      if (typeof record.msg !== 'string' || !record.msg.trim()) return null;
      const location = Array.isArray(record.loc) && record.loc.length > 0
        ? ` (${record.loc.filter((part) => typeof part === 'string' || typeof part === 'number').join('.')})`
        : '';
      return `${record.msg}${location}`;
    }).filter((message): message is string => Boolean(message));
    if (messages.length > 0) return messages.join('; ');
  }
  return fallback;
}

export async function checkBackendHealth(): Promise<BackendHealthResponse> {
  try {
    const res = await fetch(`${API_BASE_URL}/health`);
    const payload = await res.json().catch(() => ({}));
    if (!res.ok) {
      return { status: 'UNAVAILABLE', version: 'unknown', components: { backend: 'not_connected' }, uptime_s: 0 };
    }
    return {
      status: payload.status ?? 'ok',
      version: payload.version ?? 'unknown',
      components: payload.components ?? {},
      uptime_s: typeof payload.uptime_s === 'number' ? payload.uptime_s : 0,
    };
  } catch (error) {
    console.warn('[API] Health check failed:', error);
    return { status: 'OFFLINE', version: 'unknown', components: { backend: 'not_connected' }, uptime_s: 0 };
  }
}

export async function getRuntimeStatus(): Promise<RuntimeStatus | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/runtime/status`, { cache: 'no-store' });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function getCameraStatus(): Promise<CameraStatus | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/camera/status`, { cache: 'no-store' });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function getDetectorStatus(): Promise<DetectorStatus | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/detector/status`, { cache: 'no-store' });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function fetchDetections(): Promise<BackendDetection[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/detections?limit=100`, { cache: 'no-store' });
    if (!res.ok) return [];
    const payload = await res.json();
    return Array.isArray(payload) ? payload : [];
  } catch {
    return [];
  }
}

export async function fetchMission(): Promise<BackendMissionCard | null> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/mission`);
  } catch {
    throw new ApiRequestError('Backend unavailable.', 0);
  }

  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    throw new ApiRequestError(formatApiDetail(payload && typeof payload === 'object' ? payload.detail : undefined, 'Mission data is unavailable.'), response.status);
  }
  return payload as BackendMissionCard;
}

export async function saveMission(card: BackendMissionCard): Promise<MissionWriteResponse> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}/mission`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(card)
    });
  } catch {
    throw new ApiRequestError('Backend unavailable.', 0);
  }

  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new ApiRequestError(formatApiDetail(payload && typeof payload === 'object' ? payload.detail : undefined, 'Mission validation failed.'), response.status);
  }

  return {
    status: typeof payload.status === 'string' ? payload.status : 'OK',
    mission_id: typeof payload.mission_id === 'string' ? payload.mission_id : card.missionId ?? '',
    message: typeof payload.message === 'string' ? payload.message : 'Mission saved.'
  };
}

export async function fetchGovernorState(): Promise<Record<string, any> | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/governor/state`, { cache: 'no-store' });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function fetchCommunicationStatus(): Promise<Record<string, any> | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/comm/state`, { cache: 'no-store' });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export interface FlightStatus {
  status: string;
  mode: string;
  is_connected: boolean;
  is_armed: boolean;
  flight_mode: string;
  link_status: string;
  battery_percent: number;
  altitude_m: number;
  lat: number;
  lng: number;
  message?: string;
}

export interface FlightCommandResult {
  command: string;
  status: 'ACCEPTED' | 'REJECTED' | 'FAILED' | 'ACK_UNKNOWN' | string;
  ack?: string | null;
  message: string;
  timestamp?: string;
  target_altitude?: number;
  success: boolean;
}

export async function getFlightStatus(): Promise<FlightStatus | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/flight/status`, { cache: 'no-store' });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function connectSimulator(
  mode: 'cloud' | 'local' | 'fallback' = 'local',
  host?: string,
  port?: number,
  endpoint?: string
): Promise<{ status: string; mode: string; isConnected: boolean }> {
  const effectiveEndpoint = endpoint ?? (mode === 'local' ? 'udp:172.30.16.1:14550' : undefined);
  const res = await fetch(`${API_BASE_URL}/flight/connect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode, host, port, endpoint: effectiveEndpoint })
  });
  const data = await res.json().catch(() => ({ status: 'FAILED', mode, isConnected: false }));
  return { status: data.status ?? 'FAILED', mode: data.mode ?? mode, isConnected: Boolean(data.isConnected) };
}

export async function disconnectSimulator(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE_URL}/flight/disconnect`, { method: 'POST' });
    return res.ok;
  } catch {
    return false;
  }
}

export async function armDrone(): Promise<FlightCommandResult> {
  const res = await fetch(`${API_BASE_URL}/flight/arm`, { method: 'POST' });
  const payload = await res.json().catch(() => ({}));
  return normalizeFlightCommand(payload, 'ARM', res.ok);
}

export async function disarmDrone(): Promise<FlightCommandResult> {
  const res = await fetch(`${API_BASE_URL}/flight/disarm`, { method: 'POST' });
  const payload = await res.json().catch(() => ({}));
  return normalizeFlightCommand(payload, 'DISARM', res.ok);
}

export async function takeoffDrone(altitude: number = 10.0): Promise<FlightCommandResult> {
  const res = await fetch(`${API_BASE_URL}/flight/takeoff`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ altitude })
  });
  const payload = await res.json().catch(() => ({}));
  return normalizeFlightCommand(payload, 'TAKEOFF', res.ok, altitude);
}

export async function landDrone(): Promise<FlightCommandResult> {
  const res = await fetch(`${API_BASE_URL}/flight/land`, { method: 'POST' });
  const payload = await res.json().catch(() => ({}));
  return normalizeFlightCommand(payload, 'LAND', res.ok);
}

export async function hoverDrone(): Promise<FlightCommandResult> {
  const res = await fetch(`${API_BASE_URL}/flight/hover`, { method: 'POST' });
  const payload = await res.json().catch(() => ({}));
  return normalizeFlightCommand(payload, 'LOITER', res.ok);
}

export async function moveDrone(vx: number, vy: number, vz: number, yawRate: number = 0): Promise<{ status: string; success: boolean }> {
  const res = await fetch(`${API_BASE_URL}/flight/move`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ vx, vy, vz, yaw_rate: yawRate })
  });
  return await res.json();
}

export async function setHeadingDrone(heading: number): Promise<FlightCommandResult> {
  const res = await fetch(`${API_BASE_URL}/flight/heading`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ heading })
  });
  const payload = await res.json().catch(() => ({}));
  return normalizeFlightCommand(payload, 'HEADING', res.ok);
}

export async function returnToHomeDrone(): Promise<FlightCommandResult> {
  const res = await fetch(`${API_BASE_URL}/flight/rth`, { method: 'POST' });
  const payload = await res.json().catch(() => ({}));
  return normalizeFlightCommand(payload, 'RTL', res.ok);
}

function normalizeFlightCommand(payload: any, command: string, requestSucceeded: boolean, altitude?: number): FlightCommandResult {
  const success = payload?.success === true && requestSucceeded;
  return {
    command: typeof payload?.command === 'string' ? payload.command : command,
    status: typeof payload?.status === 'string' ? payload.status : requestSucceeded ? 'ACK_UNKNOWN' : 'FAILED',
    ack: typeof payload?.ack === 'string' ? payload.ack : null,
    message: typeof payload?.message === 'string' && payload.message.trim() ? payload.message : 'No command result message received.',
    timestamp: typeof payload?.timestamp === 'string' ? payload.timestamp : undefined,
    target_altitude: typeof payload?.target_altitude === 'number' ? payload.target_altitude : altitude,
    success
  };
}

export interface FlightCommandLogEntry {
  timestamp: string;
  command: string;
  status: string;
  detail?: string;
}

export async function getFlightCommandLog(): Promise<{ state: string; entries: FlightCommandLogEntry[] }> {
  try {
    const res = await fetch(`${API_BASE_URL}/flight/commands`, { cache: 'no-store' });
    if (!res.ok) return { state: 'DISCONNECTED', entries: [] };
    const data = await res.json();
    return { state: data.state ?? 'DISCONNECTED', entries: Array.isArray(data.entries) ? data.entries : [] };
  } catch {
    return { state: 'DISCONNECTED', entries: [] };
  }
}

export interface MissionUploadResult {
  command: string;
  status: string;
  success: boolean;
  ack?: string | null;
  message: string;
  waypoints: number;
}

export async function uploadMission(): Promise<MissionUploadResult> {
  const res = await fetch(`${API_BASE_URL}/mission/upload`, { method: 'POST' });
  const payload = await res.json().catch(() => ({}));
  return {
    command: typeof payload.command === 'string' ? payload.command : 'MISSION UPLOAD',
    status: typeof payload.status === 'string' ? payload.status : res.ok ? 'ACK_UNKNOWN' : 'FAILED',
    success: payload.success === true && res.ok,
    ack: typeof payload.ack === 'string' ? payload.ack : null,
    message: typeof payload.message === 'string' && payload.message.trim() ? payload.message : 'No mission upload result received.',
    waypoints: typeof payload.waypoints === 'number' ? payload.waypoints : 0
  };
}

export const CAMERA_FRAME_URL = `${API_BASE_URL}/camera/frame`;
export const CAMERA_STREAM_URL = `${API_BASE_URL}/camera/stream`;


