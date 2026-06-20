import { useEffect, useState } from 'react';
import { fetchTimeline } from '@/lib/api';
import type { LifecycleEvent } from '@/types';

const POLL_MS = 10000; // lifecycle events are infrequent; a slow poll suffices

export interface TimelineState {
  events: LifecycleEvent[];
  error: string | null;
}

// Poll the server-retained lifecycle timeline. Unlike the live SSE feed, this
// survives a page reload, so the dashboard can show recent activity on load.
export function useTimeline(limit = 12): TimelineState {
  const [state, setState] = useState<TimelineState>({ events: [], error: null });

  useEffect(() => {
    let alive = true;

    const poll = async () => {
      try {
        const events = await fetchTimeline(limit);
        if (alive) setState({ events, error: null });
      } catch (err) {
        if (alive) {
          setState((s) => ({ ...s, error: err instanceof Error ? err.message : 'failed' }));
        }
      }
    };

    void poll();
    const id = setInterval(poll, POLL_MS);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [limit]);

  return state;
}
