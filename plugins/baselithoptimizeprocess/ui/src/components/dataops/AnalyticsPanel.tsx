import { useEffect, useState } from 'react';

import { api } from '../../api/client';
import type { MiningResult } from '../../api/types';
import { formatNumber } from '../../lib/ui';

/** Variant analysis + activity statistics from the latest mining run. */
export function AnalyticsPanel({ processId }: { processId: string }) {
  const [result, setResult] = useState<MiningResult | null>(null);
  const [missing, setMissing] = useState(false);

  useEffect(() => {
    setResult(null);
    setMissing(false);
    void api
      .getMining(processId)
      .then(setResult)
      .catch(() => setMissing(true));
  }, [processId]);

  if (missing) {
    return (
      <div className="glass p-6 text-sm text-slate-400">
        <p className="font-medium text-slate-200">No mining analytics available</p>
        <p className="mt-1 max-w-2xl">
          Create this process via <span className="text-accent-soft">Mine From Log</span> to unlock
          variant, throughput and rework analysis.
        </p>
      </div>
    );
  }
  if (!result) return <p className="text-sm text-slate-500">Loading analytics…</p>;

  const maxCount = Math.max(...result.variants.map((v) => v.count), 1);

  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Cases" value={`${result.case_count}`} />
        <Stat label="Variants" value={`${result.variants.length}`} />
        <Stat label="Avg case time" value={`${formatNumber(result.avg_case_duration_seconds)} s`} />
        <Stat label="Rework cases" value={`${Math.round(result.rework_rate * 100)}%`} />
      </div>

      {(result.self_loops.length > 0 || result.concurrent_activities.length > 0) && (
        <div className="flex flex-wrap gap-4">
          {result.self_loops.length > 0 && (
            <div className="glass flex-1 p-3">
              <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-sev-high">
                Rework loops
              </p>
              <div className="flex flex-wrap gap-1">
                {result.self_loops.map((a) => (
                  <span key={a} className="chip bg-sev-high/10 text-sev-high">
                    {a} ↺
                  </span>
                ))}
              </div>
            </div>
          )}
          {result.concurrent_activities.length > 0 && (
            <div className="glass flex-1 p-3">
              <p className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-accent-soft">
                Likely parallel
              </p>
              <div className="flex flex-wrap gap-1">
                {result.concurrent_activities.map((pair, i) => (
                  <span key={i} className="chip bg-accent/10 text-accent-soft">
                    {pair.join(' ∥ ')}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      <section>
        <h2 className="mb-2 text-sm font-semibold text-slate-200">Path Variants</h2>
        <ul className="space-y-2">
          {result.variants.map((v, i) => (
            <li key={i} className="glass p-3">
              <div className="mb-1.5 flex items-center justify-between text-xs text-slate-400">
                <span>{v.count} case(s)</span>
                <span>{formatNumber(v.avg_duration_seconds)} s avg</span>
              </div>
              <div className="mb-2 h-1.5 overflow-hidden rounded-full bg-white/5">
                <div
                  className="h-full rounded-full bg-accent-deep"
                  style={{ width: `${(v.count / maxCount) * 100}%` }}
                />
              </div>
              <div className="flex flex-wrap items-center gap-1">
                {v.sequence.map((step, j) => (
                  <span key={j} className="flex min-w-0 items-center gap-1">
                    <span className="chip max-w-56 truncate bg-white/5 text-slate-300">{step}</span>
                    {j < v.sequence.length - 1 && <span className="text-slate-600">→</span>}
                  </span>
                ))}
              </div>
            </li>
          ))}
        </ul>
      </section>

      <section>
        <h2 className="mb-2 text-sm font-semibold text-slate-200">Activities</h2>
        <div className="glass divide-y divide-white/5">
          {result.activity_stats.map((a) => (
            <div
              key={a.activity}
              className="flex items-center justify-between gap-3 px-3.5 py-2 text-sm"
            >
              <span className="min-w-0 truncate text-slate-200">{a.activity}</span>
              <span className="shrink-0 text-xs text-slate-500">
                {a.occurrences}× · {formatNumber(a.avg_wait_seconds)} s wait
                {a.rework_count > 0 && (
                  <span className="ml-1 text-sev-high">· {a.rework_count} rework</span>
                )}
              </span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric-card">
      <p className="text-[11px] uppercase tracking-wide text-slate-500">{label}</p>
      <p className="number mt-1 text-xl font-semibold text-accent-soft">{value}</p>
    </div>
  );
}
