import { Activity, Target } from 'lucide-react';
import { motion } from 'motion/react';

import type { KpiDefinition, KpiSnapshot } from '../api/types';
import { cn, formatNumber } from '../lib/ui';

interface KpiMonitorProps {
  kpis: KpiDefinition[];
  snapshots: KpiSnapshot[];
  connected: boolean;
}

/**
 * Fraction of target attainment in [0,1] — honest health, not a placeholder.
 * For maximize KPIs, full bar means at/above target; for minimize, at/below.
 */
function attainment(value: number, target: number | null, direction: string): number {
  if (target === null || target === 0) return 1;
  const ratio = direction === 'minimize' ? target / Math.max(value, 1e-9) : value / target;
  return Math.max(0.04, Math.min(1, ratio));
}

/** Live KPI gauges, one card per defined metric, breach-highlighted. */
export function KpiMonitor({ kpis, snapshots, connected }: KpiMonitorProps) {
  const byId = new Map(snapshots.map((s) => [s.kpi_id, s]));

  return (
    <div>
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-accent/10 text-accent-soft">
            <Activity size={16} aria-hidden="true" />
          </span>
          <div>
            <h2 className="text-sm font-semibold text-slate-100">KPI Health</h2>
            <p className="text-xs text-slate-500">Latest sample per KPI, from the live stream.</p>
          </div>
        </div>
        <div className="flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-3 py-1.5">
          <span
            className={cn(
              'h-2 w-2 rounded-full',
              connected ? 'animate-pulse bg-sev-low' : 'bg-slate-600'
            )}
          />
          <span className="text-xs text-slate-400" aria-live="polite">
            {connected ? 'Live streaming' : 'Idle'}
          </span>
        </div>
      </div>

      {kpis.length === 0 ? (
        <div className="glass p-5 text-sm text-slate-500">
          No KPIs defined for this process. Add KPIs in Edit Map to monitor health and detect
          bottlenecks.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {kpis.map((kpi) => {
            const snap = byId.get(kpi.id);
            const breaching = snap?.breaching ?? false;
            const target = snap?.target ?? kpi.target;
            const fill = snap ? attainment(snap.value, target, kpi.direction) : 0;
            return (
              <motion.div
                key={kpi.id}
                layout
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className={cn(
                  'glass glass-hover p-4',
                  breaching && 'border-sev-critical/40 ring-1 ring-sev-critical/40'
                )}
              >
                <div className="flex min-w-0 items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-slate-100">{kpi.name}</p>
                    <p className="mt-0.5 text-[11px] uppercase tracking-wide text-slate-500">
                      {kpi.direction === 'minimize' ? 'lower is better' : 'higher is better'}
                    </p>
                  </div>
                  {breaching && (
                    <span className="chip bg-sev-critical/15 text-sev-critical">breach</span>
                  )}
                </div>
                <div className="mt-3 flex items-baseline gap-1.5">
                  <span
                    className={cn(
                      'number text-3xl font-semibold',
                      breaching ? 'text-sev-critical' : 'text-slate-50'
                    )}
                  >
                    {snap ? formatNumber(snap.value) : '—'}
                  </span>
                  <span className="text-xs text-slate-500">{kpi.unit}</span>
                </div>
                <div
                  className="mt-3 h-1.5 overflow-hidden rounded-full bg-white/[0.06]"
                  role="meter"
                  aria-valuenow={Math.round(fill * 100)}
                  aria-valuemin={0}
                  aria-valuemax={100}
                  aria-label={`${kpi.name} attainment`}
                >
                  <motion.div
                    className={cn(
                      'h-full rounded-full',
                      breaching ? 'bg-sev-critical' : 'bg-sev-low'
                    )}
                    initial={{ width: 0 }}
                    animate={{ width: `${fill * 100}%` }}
                    transition={{ type: 'spring', stiffness: 200, damping: 28 }}
                  />
                </div>
                <div className="mt-2 flex items-center justify-between text-[11px] text-slate-500">
                  <span>
                    {snap ? `${formatNumber(snap.sample_count)} samples` : 'No samples yet'}
                  </span>
                  {target !== null && (
                    <span className="inline-flex items-center gap-1">
                      <Target size={11} aria-hidden="true" />
                      target {formatNumber(target)}
                    </span>
                  )}
                </div>
              </motion.div>
            );
          })}
        </div>
      )}
    </div>
  );
}
