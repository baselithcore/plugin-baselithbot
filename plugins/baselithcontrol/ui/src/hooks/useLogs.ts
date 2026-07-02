import { useEffect, useState } from 'react';
import { fetchLogs, type LogQuery } from '@/lib/api';
import { usePoll } from '@/hooks/usePoll';
import type { LogsView } from '@/types';

const POLL_MS = 2500;
const DEBOUNCE_MS = 300;

export interface LogsState {
  data: LogsView | null;
  loading: boolean;
  error: string | null;
}

// Poll the admin-only log tail with the active filters. Re-fetches immediately
// when the query changes (the free-text term is debounced so typing doesn't
// fire a request per keystroke); stops polling while `paused` (so an operator
// can read a frozen view). Keeps the last good data on a transient error.
export function useLogs(query: LogQuery, paused: boolean): LogsState {
  const [state, setState] = useState<LogsState>({
    data: null,
    loading: true,
    error: null,
  });

  // Debounced search term — select/limit filters still apply instantly.
  const [q, setQ] = useState(query.q);
  useEffect(() => {
    const id = window.setTimeout(() => setQ(query.q), DEBOUNCE_MS);
    return () => window.clearTimeout(id);
  }, [query.q]);

  const effective: LogQuery = { ...query, q };
  // Serialize the effective query so the poller re-keys only on a real change.
  const key = JSON.stringify(effective);

  const load = async (alive: () => boolean): Promise<boolean> => {
    try {
      const data = await fetchLogs(effective);
      if (alive()) setState({ data, loading: false, error: null });
      return true;
    } catch (err) {
      if (alive()) {
        setState((s) => ({
          ...s,
          loading: false,
          error: err instanceof Error ? err.message : 'failed',
        }));
      }
      return false;
    }
  };

  usePoll(load, { intervalMs: POLL_MS, enabled: !paused, key });

  // While paused we still fetch once per filter change, so the frozen view
  // reflects whatever filters the operator sets.
  useEffect(() => {
    if (!paused) return;
    let alive = true;
    void load(() => alive);
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [paused, key]);

  return state;
}
