import { useEffect, useRef, useState } from 'react';
import { fetchLogs, type LogQuery } from '@/lib/api';
import type { LogsView } from '@/types';

const POLL_MS = 2500;

export interface LogsState {
  data: LogsView | null;
  loading: boolean;
  error: string | null;
}

// Poll the admin-only log tail with the active filters. Re-fetches immediately
// when the query changes; stops polling while `paused` (so an operator can read
// a frozen view). Keeps the last good data on a transient error.
export function useLogs(query: LogQuery, paused: boolean): LogsState {
  const [state, setState] = useState<LogsState>({
    data: null,
    loading: true,
    error: null,
  });
  const alive = useRef(true);
  // Serialize the query so the effect re-runs only on a real change.
  const key = JSON.stringify(query);

  useEffect(() => {
    alive.current = true;

    const load = async () => {
      try {
        const data = await fetchLogs(query);
        if (!alive.current) return;
        setState({ data, loading: false, error: null });
      } catch (err) {
        if (!alive.current) return;
        setState((s) => ({
          ...s,
          loading: false,
          error: err instanceof Error ? err.message : 'failed',
        }));
      }
    };

    void load();
    if (paused) return () => void (alive.current = false);

    const id = setInterval(load, POLL_MS);
    return () => {
      alive.current = false;
      clearInterval(id);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, paused]);

  return state;
}
