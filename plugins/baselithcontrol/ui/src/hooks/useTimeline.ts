import { useState } from 'react';
import { fetchTimeline } from '@/lib/api';
import { usePoll } from '@/hooks/usePoll';
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

  usePoll(
    async (alive) => {
      try {
        const events = await fetchTimeline(limit);
        if (alive()) setState({ events, error: null });
        return true;
      } catch (err) {
        if (alive()) {
          setState((s) => ({ ...s, error: err instanceof Error ? err.message : 'failed' }));
        }
        return false;
      }
    },
    { intervalMs: POLL_MS, key: String(limit) }
  );

  return state;
}
