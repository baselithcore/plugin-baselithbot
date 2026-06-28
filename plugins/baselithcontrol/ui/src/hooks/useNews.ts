import { useEffect, useRef, useState } from 'react';
import { fetchNews } from '@/lib/api';
import type { NewsItem } from '@/types';

// The server caches each snapshot for ~10 min, so polling more often than that
// just returns the same payload. Refresh a little faster than the TTL to pick
// changes up promptly, plus on tab refocus so a long-idle dashboard isn't stale.
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
  const alive = useRef(true);

  useEffect(() => {
    alive.current = true;

    const load = async () => {
      try {
        const res = await fetchNews();
        if (!alive.current) return;
        setState({ items: res.items, loading: false, error: null, stale: res.stale });
      } catch (err) {
        if (!alive.current) return;
        // Keep any previously loaded items on a transient error — the ticker
        // should not blank out just because one refresh failed.
        setState((s) => ({
          ...s,
          loading: false,
          error: err instanceof Error ? err.message : 'failed',
        }));
      }
    };

    void load();
    const id = setInterval(load, POLL_MS);
    const onVisible = () => {
      if (document.visibilityState === 'visible') void load();
    };
    document.addEventListener('visibilitychange', onVisible);

    return () => {
      alive.current = false;
      clearInterval(id);
      document.removeEventListener('visibilitychange', onVisible);
    };
  }, []);

  return state;
}
