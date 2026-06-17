import { useEffect } from 'react';
import { streamUrl } from '@/lib/api';
import { useControlStore } from '@/store/useControlStore';

// Subscribe to the control SSE feed. Unnamed `data:` frames land on onmessage;
// reconnect with capped exponential backoff on error.
export function useStatusStream(): void {
  const applyEvent = useControlStore((s) => s.applyEvent);
  const setConnected = useControlStore((s) => s.setConnected);

  useEffect(() => {
    let es: EventSource | null = null;
    let retry = 0;
    let timer: number | undefined;

    const connect = () => {
      es = new EventSource(streamUrl(), { withCredentials: true });
      es.onopen = () => {
        retry = 0;
        setConnected(true);
      };
      es.onmessage = (e) => {
        try {
          applyEvent(JSON.parse(e.data));
        } catch {
          /* ignore malformed frames */
        }
      };
      es.onerror = () => {
        setConnected(false);
        es?.close();
        retry = Math.min(retry + 1, 6);
        timer = window.setTimeout(connect, 500 * 2 ** retry);
      };
    };

    connect();
    return () => {
      es?.close();
      if (timer) window.clearTimeout(timer);
    };
  }, [applyEvent, setConnected]);
}
