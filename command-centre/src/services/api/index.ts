export const API_BASE_URL = 'http://127.0.0.1:8000/api/v1';

export interface BackendHealthResponse {
  status: string;
  version: string;
  components: Record<string, string>;
  uptime_s: number;
}

export interface BackendTelemetry {
  timestamp_utc: string;
  latitude: number;
  longitude: number;
  altitude_m: number;
  ground_speed_ms: number;
  heading_deg: number;
  battery_remaining_pct: number;
  flight_mode: string;
  is_armed: boolean;
  rf_link_active: boolean;
}

export interface BackendGovernorState {
  current_decision: string;
  last_reason: string;
  evaluation_time_utc: string;
  decisions_total: number;
  events_transmitted: number;
  retained_count: number;
  suppressed_count: number;
}

export interface BackendCommState {
  link_state: string;
  total_bytes_transmitted: number;
  event_packets_sent: number;
  evidence_packets_sent: number;
  suppressed_count: number;
  retained_count: number;
  last_tx_timestamp: string | null;
  avg_tx_latency_ms: number;
}

export async function checkBackendHealth(): Promise<BackendHealthResponse> {
  try {
    const res = await fetch(`${API_BASE_URL}/health`);
    if (!res.ok) {
      return { status: 'UNAVAILABLE', version: 'unknown', components: {}, uptime_s: 0 };
    }
    return await res.json();
  } catch {
    return { status: 'STANDBY_MOCK_ACTIVE', version: '1.0.0', components: { backend: 'OFFLINE' }, uptime_s: 0 };
  }
}

export async function fetchTelemetry(): Promise<BackendTelemetry | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/telemetry`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function fetchMission(): Promise<Record<string, any> | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/mission`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function fetchGovernorState(): Promise<BackendGovernorState | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/governor/state`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function fetchCommState(): Promise<BackendCommState | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/comm/state`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function fetchCommEvents(): Promise<any[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/comm/events`);
    if (!res.ok) return [];
    return await res.json();
  } catch {
    return [];
  }
}

export async function fetchCommEvidence(): Promise<any[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/comm/evidence`);
    if (!res.ok) return [];
    return await res.json();
  } catch {
    return [];
  }
}

export async function fetchRetained(): Promise<any[]> {
  try {
    const res = await fetch(`${API_BASE_URL}/comm/retained`);
    if (!res.ok) return [];
    return await res.json();
  } catch {
    return [];
  }
}

export async function setCommLink(enabled: boolean): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE_URL}/comm/link?enabled=${enabled}`, { method: 'POST' });
    return res.ok;
  } catch {
    return false;
  }
}

// ─────────────────────────────────────────────
//  Real Flight Control API
// ─────────────────────────────────────────────

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

export async function getFlightStatus(): Promise<FlightStatus | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/flight/status`);
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

export async function connectSimulator(
  mode: 'cloud' | 'local' | 'fallback' = 'cloud',
  host?: string,
  port?: number,
  endpoint?: string
): Promise<{ status: string; mode: string; isConnected: boolean }> {
  const res = await fetch(`${API_BASE_URL}/flight/connect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ mode, host, port, endpoint })
  });
  return await res.json();
}

export async function disconnectSimulator(): Promise<boolean> {
  try {
    const res = await fetch(`${API_BASE_URL}/flight/disconnect`, { method: 'POST' });
    return res.ok;
  } catch {
    return false;
  }
}

export async function armDrone(): Promise<{ status: string; success: boolean }> {
  const res = await fetch(`${API_BASE_URL}/flight/arm`, { method: 'POST' });
  return await res.json();
}

export async function disarmDrone(): Promise<{ status: string; success: boolean }> {
  const res = await fetch(`${API_BASE_URL}/flight/disarm`, { method: 'POST' });
  return await res.json();
}

export async function takeoffDrone(altitude: number = 10.0): Promise<{ status: string; success: boolean }> {
  const res = await fetch(`${API_BASE_URL}/flight/takeoff`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ altitude })
  });
  return await res.json();
}

export async function landDrone(): Promise<{ status: string; success: boolean }> {
  const res = await fetch(`${API_BASE_URL}/flight/land`, { method: 'POST' });
  return await res.json();
}

export async function hoverDrone(): Promise<{ status: string; success: boolean }> {
  const res = await fetch(`${API_BASE_URL}/flight/hover`, { method: 'POST' });
  return await res.json();
}

export async function moveDrone(
  vx: number,
  vy: number,
  vz: number,
  yawRate: number = 0
): Promise<{ status: string; success: boolean }> {
  const res = await fetch(`${API_BASE_URL}/flight/move`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ vx, vy, vz, yaw_rate: yawRate })
  });
  return await res.json();
}

export async function setHeadingDrone(heading: number): Promise<{ status: string; success: boolean }> {
  const res = await fetch(`${API_BASE_URL}/flight/heading`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ heading })
  });
  return await res.json();
}

export async function returnToHomeDrone(): Promise<{ status: string; success: boolean }> {
  const res = await fetch(`${API_BASE_URL}/flight/rth`, { method: 'POST' });
  return await res.json();
}

export const CAMERA_FRAME_URL = `${API_BASE_URL}/camera/frame`;
export const CAMERA_STREAM_URL = `${API_BASE_URL}/camera/stream`;


