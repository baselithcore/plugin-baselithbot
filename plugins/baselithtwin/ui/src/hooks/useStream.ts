// Subscribes to the backend Server-Sent Events feed and keeps a bounded,
// newest-first ring of recent events for the live activity panel. Auto-reconnts
// via the browser's native EventSource backoff; an onEvent callback lets callers
// refresh dependent data (status, queue) when a relevant event arrives.

import { useEffect, useRef, useState } from 'react';
import { STREAM_URL } from '../api/client';
import type { StreamEvent } from '../api/types';

const MAX_EVENTS = 50;

export function useStream(onEvent?: (event: StreamEvent) => void) {
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const cb = useRef(onEvent);
  cb.current = onEvent;

  useEffect(() => {
    const source = new EventSource(STREAM_URL);
    source.onopen = () => setConnected(true);
    source.onerror = () => setConnected(false);
    source.onmessage = (msg) => {
      try {
        const event = JSON.parse(msg.data) as StreamEvent;
        setEvents((prev) => [event, ...prev].slice(0, MAX_EVENTS));
        cb.current?.(event);
      } catch {
        /* ignore malformed frames */
      }
    };
    return () => source.close();
  }, []);

  return { events, connected };
}
