import { useEffect, useState } from 'react';
import { GlassPanel } from '../components/GlassPanel';
import { Skeleton } from '../components/Skeleton';
import { api } from '../lib/api';
import type { AgentRunResult } from '../lib/types';

const STATUS_TINT: Record<string, string> = {
  succeeded: 'text-emerald-300',
  failed: 'text-rose-400',
  rejected: 'text-amber-300',
  running: 'text-cyan',
  pending: 'text-slate-400',
};

/** Audit-style history of recent agent runs. */
export function Runs() {
  const [runs, setRuns] = useState<AgentRunResult[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .listRuns()
      .then(setRuns)
      .catch((e) => setError((e as Error).message));
  }, []);

  if (error)
    return (
      <GlassPanel title="Runs">
        <p className="text-rose-400">{error}</p>
      </GlassPanel>
    );
  if (!runs) return <Skeleton height={220} />;

  return (
    <GlassPanel title="Recent runs" subtitle={`${runs.length} retained`}>
      {runs.length === 0 ? (
        <p className="text-sm text-slate-400">No runs yet.</p>
      ) : (
        <div className="space-y-2">
          {runs.map((r) => (
            <div
              key={r.run_id}
              className="flex items-center justify-between gap-4 rounded-lg border border-ink-600/50 bg-ink-800/40 px-4 py-2.5"
            >
              <div className="min-w-0">
                <div className="flex items-center gap-2 text-sm">
                  <span className="font-mono text-slate-300">{r.blueprint_id}</span>
                  <span className="rounded bg-ink-700/70 px-1.5 py-0.5 font-mono text-[10px] text-slate-300">
                    {r.capability}
                  </span>
                </div>
                <p className="truncate text-xs text-slate-500">{r.error ?? r.explanation ?? '—'}</p>
              </div>
              <span className={`shrink-0 text-xs font-semibold ${STATUS_TINT[r.status] ?? ''}`}>
                {r.status}
              </span>
            </div>
          ))}
        </div>
      )}
    </GlassPanel>
  );
}
