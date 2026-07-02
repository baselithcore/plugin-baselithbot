import { useState } from 'react';
import { fetchNews } from '@/lib/api';
import { usePoll } from '@/hooks/usePoll';
import type { NewsItem } from '@/types';

// The server caches each snapshot for ~10 min, so polling more often than that
// just returns the same payload. Refresh a little faster than the TTL to pick
// changes up promptly. usePoll stops the loop entirely while the tab is hidden
// and refetches on refocus, so a long-idle dashboard is never stale.
const POLL_MS = 5 * 60 * 1000;

export interface NewsState {
  items: NewsItem[];
  loading: boolean;
  error: string | null;
  stale: boolean; // last good snapshot served after a refresh failure
}

export function useNews(): NewsState {
  const [state, setState] = useState<NewsState>({
    items: [],
    loading: true,
    error: null,
    stale: false,
  });

  usePoll(
    async (alive) => {
      try {
        const res = await fetchNews();
        if (alive()) setState({ items: res.items, loading: false, error: null, stale: res.stale });
        return true;
      } catch (err) {
        // Keep any previously loaded items on a transient error — the ticker
        // should not blank out just because one refresh failed.
        if (alive()) {
          setState((s) => ({
            ...s,
            loading: false,
            error: err instanceof Error ? err.message : 'failed',
          }));
        }
        return false;
      }
    },
    { intervalMs: POLL_MS }
  );

  return state;
}
