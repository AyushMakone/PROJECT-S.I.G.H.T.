// Placeholder for future WebSocket client (FastAPI MAVLink & Governor stream)
export const WS_BASE_URL = 'ws://127.0.0.1:8000/ws';

export class MissionWebSocketClient {
  private url: string;
  constructor(url: string = WS_BASE_URL) {
    this.url = url;
  }
  public connect() {
    // Will connect to real FastAPI websocket in future backend integration milestone
    return this.url;
  }
}
