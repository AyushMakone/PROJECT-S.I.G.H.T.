// Real-time WebSocket Client for Project S.I.G.H.T. Backend Gateway
// Streams genuine UAV telemetry, Governor evaluations, and communication events

export const WS_BASE_URL =
  (import.meta as any).env?.VITE_WS_URL || 'ws://127.0.0.1:8000/ws/mission';

export type WebSocketListener<T = any> = (data: T) => void;

export type ConnectionState =
  | 'SIMULATOR OFFLINE'
  | 'CONNECTING'
  | 'WAITING FOR HEARTBEAT'
  | 'CONNECTED'
  | 'TELEMETRY ACTIVE'
  | 'SIMULATOR CONNECTION LOST';

export class MissionWebSocketClient {
  private url: string;
  private ws: WebSocket | null = null;
  private reconnectAttempts: number = 0;
  private maxReconnectAttempts: number = 20;
  private reconnectIntervalMs: number = 2000;
  private pingInterval: any = null;
  private isExplicitlyClosed: boolean = false;

  private listeners: Map<string, Set<WebSocketListener>> = new Map();
  private statusListeners: Set<(status: ConnectionState) => void> = new Set();
  private currentStatus: ConnectionState = 'SIMULATOR OFFLINE';
  private lastMessageTimestamp: number = 0;

  constructor(url: string = WS_BASE_URL) {
    this.url = url;
  }

  public getStatus(): ConnectionState {
    return this.currentStatus;
  }

  public getLastMessageTimestamp(): number {
    return this.lastMessageTimestamp;
  }

  public connect(): void {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.isExplicitlyClosed = false;
    this.updateStatus('CONNECTING');

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        this.reconnectAttempts = 0;
        this.updateStatus('WAITING FOR HEARTBEAT');
        this.startHeartbeat();
      };

      this.ws.onmessage = (event: MessageEvent) => {
        this.lastMessageTimestamp = Date.now();
        try {
          const payload = JSON.parse(event.data);
          const type = payload.type || 'unknown';

          if (type === 'telemetry') {
            this.updateStatus('TELEMETRY ACTIVE');
          }

          // Dispatch to type-specific subscribers
          const handlers = this.listeners.get(type);
          if (handlers) {
            handlers.forEach((fn) => fn(payload.data || payload));
          }

          // Also dispatch to wildcard subscribers
          const allHandlers = this.listeners.get('*');
          if (allHandlers) {
            allHandlers.forEach((fn) => fn(payload));
          }
        } catch (err) {
          console.error('[WS] Failed to parse message:', err);
        }
      };

      this.ws.onerror = () => {
        if (this.currentStatus !== 'SIMULATOR CONNECTION LOST') {
          this.updateStatus('SIMULATOR CONNECTION LOST');
        }
      };

      this.ws.onclose = () => {
        this.stopHeartbeat();
        this.ws = null;
        if (!this.isExplicitlyClosed) {
          this.updateStatus('SIMULATOR CONNECTION LOST');
          this.scheduleReconnect();
        } else {
          this.updateStatus('SIMULATOR OFFLINE');
        }
      };
    } catch (err) {
      this.updateStatus('SIMULATOR CONNECTION LOST');
      this.scheduleReconnect();
    }
  }

  public disconnect(): void {
    this.isExplicitlyClosed = true;
    this.stopHeartbeat();
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.updateStatus('SIMULATOR OFFLINE');
  }

  public send(action: string, payload: any = {}): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ action, ...payload }));
    }
  }

  public on<T = any>(type: string, listener: WebSocketListener<T>): () => void {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, new Set());
    }
    this.listeners.get(type)!.add(listener);

    return () => {
      const set = this.listeners.get(type);
      if (set) {
        set.delete(listener);
      }
    };
  }

  public onStatusChange(listener: (status: ConnectionState) => void): () => void {
    this.statusListeners.add(listener);
    listener(this.currentStatus);
    return () => this.statusListeners.delete(listener);
  }

  private updateStatus(status: ConnectionState): void {
    this.currentStatus = status;
    this.statusListeners.forEach((fn) => fn(status));
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.warn('[WS] Maximum reconnect attempts reached.');
      return;
    }
    this.reconnectAttempts++;
    const delay = Math.min(10000, this.reconnectIntervalMs * Math.pow(1.3, this.reconnectAttempts - 1));
    setTimeout(() => {
      if (!this.isExplicitlyClosed) {
        this.connect();
      }
    }, delay);
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.pingInterval = setInterval(() => {
      this.send('ping');
    }, 15000);
  }

  private stopHeartbeat(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }
}

// Global shared singleton for the Command Centre
export const missionWs = new MissionWebSocketClient();
