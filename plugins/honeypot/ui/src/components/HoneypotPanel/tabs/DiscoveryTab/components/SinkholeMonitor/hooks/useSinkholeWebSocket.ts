/**
 * useSinkholeWebSocket - Real-time WebSocket hook for sinkhole updates
 *
 * Connects to backend WebSocket endpoints for live sinkhole monitoring.
 * Supports both global updates and domain-specific subscriptions.
 */

import { useEffect, useState, useCallback, useRef } from 'react';

export type SinkholeEvent =
  | 'connected'
  | 'pong'
  | 'request_intercepted'
  | 'status_changed'
  | 'domain_created'
  | 'stats_updated';

export interface SinkholeEventData {
  event: SinkholeEvent;
  message?: string;
  domain_id?: number;
  data?: any;
  timestamp?: string;
}

interface UseSinkholeWebSocketOptions {
  /** Domain ID to subscribe to (omit for global updates) */
  domainId?: number;
  /** Auto-reconnect on disconnect */
  autoReconnect?: boolean;
  /** Reconnect delay in ms */
  reconnectDelay?: number;
  /** Max reconnection attempts (0 = infinite) */
  maxReconnectAttempts?: number;
  /** Callback for connection established */
  onConnect?: () => void;
  /** Callback for connection closed */
  onDisconnect?: () => void;
  /** Callback for errors */
  onError?: (error: Event) => void;
  /** Callback for each event received */
  onEvent?: (event: SinkholeEventData) => void;
}

interface UseSinkholeWebSocketReturn {
  /** Whether WebSocket is connected */
  connected: boolean;
  /** Last event received */
  lastEvent: SinkholeEventData | null;
  /** Connection error if any */
  error: string | null;
  /** Manually reconnect */
  reconnect: () => void;
  /** Manually disconnect */
  disconnect: () => void;
  /** Send ping to server */
  sendPing: () => void;
}

const WS_BASE_URL = 'ws://localhost:8000/api/honeypot/sinkhole/ws';

export function useSinkholeWebSocket(
  options: UseSinkholeWebSocketOptions = {}
): UseSinkholeWebSocketReturn {
  const {
    domainId,
    autoReconnect = true,
    reconnectDelay = 3000,
    maxReconnectAttempts = 10,
    onConnect,
    onDisconnect,
    onError,
    onEvent,
  } = options;

  const [connected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<SinkholeEventData | null>(null);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<number>();
  const pingIntervalRef = useRef<number>();

  // Build WebSocket URL
  const wsUrl = domainId ? `${WS_BASE_URL}/domain/${domainId}` : `${WS_BASE_URL}/updates`;

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = undefined;
    }
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = undefined;
    }
    setConnected(false);
  }, []);

  const connect = useCallback(() => {
    // Clean up existing connection
    disconnect();

    try {
      // Check if we are running in MkDocs environment
      const isMkDocs = document.querySelector('meta[name="generator"][content*="mkdocs"]');
      if (isMkDocs) {
        console.debug('[WebSocket] Skipped connection (MkDocs environment detected)');
        return;
      }

      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log(`[WebSocket] Connected to ${wsUrl}`);
        setConnected(true);
        setError(null);
        reconnectAttemptsRef.current = 0;
        onConnect?.();

        // Start ping interval (every 30s)
        pingIntervalRef.current = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send('ping');
          }
        }, 30000);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data) as SinkholeEventData;
          setLastEvent(data);
          onEvent?.(data);

          // Log events (except pong)
          if (data.event !== 'pong') {
            console.log('[WebSocket] Event received:', data);
          }
        } catch (err) {
          console.error('[WebSocket] Failed to parse message:', err);
        }
      };

      ws.onerror = (event) => {
        console.error('[WebSocket] Error:', event);
        setError('WebSocket connection error');
        onError?.(event);
      };

      ws.onclose = (event) => {
        console.log('[WebSocket] Disconnected:', event.code, event.reason);
        setConnected(false);
        onDisconnect?.();

        if (pingIntervalRef.current) {
          clearInterval(pingIntervalRef.current);
          pingIntervalRef.current = undefined;
        }

        // Auto-reconnect logic
        if (
          autoReconnect &&
          (maxReconnectAttempts === 0 || reconnectAttemptsRef.current < maxReconnectAttempts)
        ) {
          reconnectAttemptsRef.current += 1;
          console.log(
            `[WebSocket] Reconnecting in ${reconnectDelay}ms (attempt ${reconnectAttemptsRef.current}/${maxReconnectAttempts || '∞'})...`
          );

          reconnectTimeoutRef.current = setTimeout(() => {
            connect();
          }, reconnectDelay);
        } else if (maxReconnectAttempts > 0) {
          setError(`Max reconnection attempts (${maxReconnectAttempts}) reached`);
        }
      };
    } catch (err) {
      console.error('[WebSocket] Connection failed:', err);
      setError(err instanceof Error ? err.message : 'Failed to connect');
    }
  }, [
    wsUrl,
    autoReconnect,
    reconnectDelay,
    maxReconnectAttempts,
    onConnect,
    onDisconnect,
    onError,
    onEvent,
    disconnect,
  ]);

  const sendPing = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send('ping');
    }
  }, []);

  // Connect on mount, disconnect on unmount
  useEffect(() => {
    connect();

    return () => {
      disconnect();
    };
  }, [connect, disconnect]);

  return {
    connected,
    lastEvent,
    error,
    reconnect: connect,
    disconnect,
    sendPing,
  };
}
