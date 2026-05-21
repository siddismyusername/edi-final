/**
 * WebSocket connection manager for the ETA-Sync dashboard.
 * Handles auto-reconnect, event dispatching, and heartbeats.
 */

export type WSEventType =
  | 'CONNECTED'
  | 'PACKET_RECEIVED'
  | 'WINDOW_READY'
  | 'DTW_COMPLETED'
  | 'FUSION_COMPLETED'
  | 'SESSION_STARTED'
  | 'SESSION_TERMINATED'
  | 'ERROR_EVENT'
  | 'HEARTBEAT'
  | 'PONG'
  | 'STATUS';

export interface WSMessage {
  event: WSEventType;
  session_id?: string;
  timestamp: number;
  data?: Record<string, unknown>;
}

export type WSEventHandler = (message: WSMessage) => void;

export class WebSocketClient {
  private ws: WebSocket | null = null;
  private url: string;
  private handlers: Map<string, Set<WSEventHandler>> = new Map();
  private globalHandlers: Set<WSEventHandler> = new Set();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private reconnectDelay = 2000;
  private maxReconnectDelay = 30000;
  private isManualClose = false;

  constructor(url: string) {
    this.url = url;
  }

  connect(): void {
    this.isManualClose = false;
    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log('[WS] Connected to', this.url);
        this.reconnectDelay = 2000;
      };

      this.ws.onmessage = (event) => {
        try {
          const message: WSMessage = JSON.parse(event.data);
          this.dispatch(message);
        } catch (e) {
          console.warn('[WS] Failed to parse message:', e);
        }
      };

      this.ws.onclose = () => {
        console.log('[WS] Disconnected');
        if (!this.isManualClose) {
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = (error) => {
        console.error('[WS] Error:', error);
      };
    } catch (e) {
      console.error('[WS] Connection failed:', e);
      this.scheduleReconnect();
    }
  }

  disconnect(): void {
    this.isManualClose = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }
    this.ws?.close();
    this.ws = null;
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) return;
    console.log(`[WS] Reconnecting in ${this.reconnectDelay}ms...`);
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, this.reconnectDelay);
    this.reconnectDelay = Math.min(this.reconnectDelay * 1.5, this.maxReconnectDelay);
  }

  on(event: WSEventType | '*', handler: WSEventHandler): () => void {
    if (event === '*') {
      this.globalHandlers.add(handler);
      return () => this.globalHandlers.delete(handler);
    }
    if (!this.handlers.has(event)) {
      this.handlers.set(event, new Set());
    }
    this.handlers.get(event)!.add(handler);
    return () => this.handlers.get(event)?.delete(handler);
  }

  private dispatch(message: WSMessage): void {
    // Notify global handlers
    this.globalHandlers.forEach((h) => h(message));

    // Notify event-specific handlers
    const eventHandlers = this.handlers.get(message.event);
    if (eventHandlers) {
      eventHandlers.forEach((h) => h(message));
    }
  }

  send(data: string): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(data);
    }
  }

  get isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}
