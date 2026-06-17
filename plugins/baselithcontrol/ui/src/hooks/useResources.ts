import { useEffect, useRef, useState } from 'react';
import { fetchPluginRuntime, fetchResources } from '@/lib/api';
import type { PluginRuntime, SystemResources } from '@/types';

const HISTORY = 40; // sparkline points retained per series
const POLL_MS = 3000;

export interface RuntimeRow extends PluginRuntime {
  rps: number; // requests/sec, derived from the monotonic counter between polls
}

export interface ResourcesState {
  resources: SystemResources | null;
  cpuHistory: number[];
  memHistory: number[];
  netHistory: number[]; // sent+recv bytes/s
  plugins: RuntimeRow[];
  error: string | null;
}

function push(arr: number[], v: number): number[] {
  const next = [...arr, v];
  return next.length > HISTORY ? next.slice(next.length - HISTORY) : next;
}

// Poll resource gauges + per-plugin request telemetry. Request *rate* is derived
// here from the monotonic `requests` counter so it stays correct regardless of
// server load (the backend deliberately does not compute rate itself).
export function useResources(): ResourcesState {
  const [state, setState] = useState<ResourcesState>({
    resources: null,
    cpuHistory: [],
    memHistory: [],
    netHistory: [],
    plugins: [],
    error: null,
  });
  // prev request counts + timestamp, kept across polls to compute rps.
  const prev = useRef<{ at: number; counts: Record<string, number> }>({ at: 0, counts: {} });

  useEffect(() => {
    let alive = true;

    const poll = async () => {
      try {
        const [res, runtime] = await Promise.all([fetchResources(), fetchPluginRuntime()]);
        if (!alive) return;

        const now = Date.now();
        const dt = prev.current.at ? (now - prev.current.at) / 1000 : 0;
        const counts: Record<string, number> = {};
        const rows: RuntimeRow[] = runtime.map((r) => {
          counts[r.plugin] = r.requests;
          const before = prev.current.counts[r.plugin];
          const rps = dt > 0 && before != null ? Math.max(0, (r.requests - before) / dt) : 0;
          return { ...r, rps: Math.round(rps * 100) / 100 };
        });
        prev.current = { at: now, counts };

        setState((s) => ({
          resources: res,
          cpuHistory: push(s.cpuHistory, res.cpu_percent ?? 0),
          memHistory: push(s.memHistory, res.rss_percent ?? res.mem_percent ?? 0),
          netHistory: push(s.netHistory, (res.net_sent_bps ?? 0) + (res.net_recv_bps ?? 0)),
          plugins: rows,
          error: null,
        }));
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
  }, []);

  return state;
}
