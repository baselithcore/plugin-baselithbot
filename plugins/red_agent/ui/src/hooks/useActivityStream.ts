import { useEffect, useRef, useState } from 'react';
import { openActivityStream, type ActivityEvent } from '../lib/api';

export interface UseActivityStreamOptions {
  /** Optional event-name predicate; events failing this are dropped. */
  filter?: (event: ActivityEvent) => boolean;
  /** Optional engagement scope (UI-side filter on payload / scan_id). */
  engagementScanIds?: Set<string>;
  /** Maximum events kept in the buffer. Default 25. */
  bufferSize?: number;
  /**
   * Server-side event-name prefixes; the WebSocket drops non-matching
   * frames before sending. Use to reduce bandwidth on busy feeds.
   */
  serverEventPrefix?: string[];
  /** Server-side engagement scope; only frames for this engagement are sent. */
  serverEngagementId?: string;
}

const RETRY_INITIAL_MS = 1_000;
const RETRY_MAX_MS = 30_000;

/**
 * Subscribes to ``/red-agent/ws/activity`` with exponential-backoff
 * reconnect. Returns a buffered list of recent events plus a connection
 * status flag the UI can render. Designed to layer on top of a polled
 * seed query — the caller dedupes by event id.
 */
export function useActivityStream(opts: UseActivityStreamOptions = {}) {
  const {
    filter,
    engagementScanIds,
    bufferSize = 25,
    serverEventPrefix,
    serverEngagementId,
  } = opts;
  const prefixKey = (serverEventPrefix ?? []).join('|');
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [nextRetryAt, setNextRetryAt] = useState<number | null>(null);
  const filterRef = useRef(filter);
  filterRef.current = filter;
  const scopeRef = useRef(engagementScanIds);
  scopeRef.current = engagementScanIds;

  useEffect(() => {
    let stopped = false;
    let socket: WebSocket | null = null;
    let retryMs = RETRY_INITIAL_MS;
    let retryHandle: number | undefined;

    const connect = () => {
      if (stopped) return;
      setNextRetryAt(null);
      try {
        socket = openActivityStream({
          eventPrefix: serverEventPrefix,
          engagementId: serverEngagementId,
        });
      } catch {
        scheduleRetry();
        return;
      }
      socket.onopen = () => {
        retryMs = RETRY_INITIAL_MS;
        setConnected(true);
        setNextRetryAt(null);
      };
      socket.onmessage = (msg) => {
        let parsed: unknown;
        try {
          parsed = JSON.parse(msg.data);
        } catch {
          return;
        }
        if (parsed && typeof parsed === 'object' && (parsed as { type?: string }).type === 'ping') {
          // Heartbeat from server — keeps the connection alive past
          // intermediary idle timeouts. Skip the buffer.
          return;
        }
        const ev = parsed as ActivityEvent;
        if (filterRef.current && !filterRef.current(ev)) return;
        if (scopeRef.current && (!ev.scan_id || !scopeRef.current.has(ev.scan_id))) return;
        setEvents((prev) => [ev, ...prev].slice(0, bufferSize));
      };
      socket.onerror = () => {
        // onclose handles cleanup + retry — just flip status.
        setConnected(false);
      };
      socket.onclose = () => {
        setConnected(false);
        scheduleRetry();
      };
    };

    const scheduleRetry = () => {
      if (stopped) return;
      setNextRetryAt(Date.now() + retryMs);
      retryHandle = window.setTimeout(connect, retryMs);
      retryMs = Math.min(retryMs * 2, RETRY_MAX_MS);
    };

    connect();

    return () => {
      stopped = true;
      if (retryHandle) window.clearTimeout(retryHandle);
      if (socket) socket.close();
    };
    // Reconnect when prefix list or engagement scope changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bufferSize, prefixKey, serverEngagementId]);

  return { events, connected, nextRetryAt };
}
