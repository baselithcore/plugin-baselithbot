import { Crosshair, User, Workflow, GitBranch, RefreshCw } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

import { api } from '../../api/client';
import type { EventFilter, FactorDimension, RootCauseReport } from '../../api/types';
import { cn, formatDuration } from '../../lib/ui';
import { FilterBar } from './FilterBar';
import { PanelEmpty, PanelLoader } from './states';

const DIMENSION_ICON: Record<FactorDimension, typeof User> = {
  resource: User,
  activity: Workflow,
  variant: GitBranch,
  pattern: RefreshCw,
};

/** Root-cause analysis: which case attributes drive slow cases. */
export function RootCausePanel({ processId }: { processId: string }) {
  const [report, setReport] = useState<RootCauseReport | null>(null);
  const [missing, setMissing] = useState(false);
  const [filter, setFilter] = useState<EventFilter>({});

  const load = useCallback(
    (f: EventFilter) => {
      setReport(null);
      setMissing(false);
      void api
        .rootCause(processId, undefined, f)
        .then((r) => (r.total_cases === 0 ? setMissing(true) : setReport(r)))
        .catch(() => setMissing(true));
    },
    [processId]
  );

  useEffect(() => load(filter), [load, filter]);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2.5">
        <span className="grid h-8 w-8 place-items-center rounded-lg bg-accent/10 text-accent-soft">
          <Crosshair size={16} aria-hidden="true" />
        </span>
        <div>
          <h2 className="text-sm font-semibold text-slate-100">Root-Cause Analysis</h2>
          <p className="text-sm text-slate-400">
            Attributes most over-represented among slow cases.
          </p>
        </div>
      </div>

      <FilterBar onApply={setFilter} />

      {missing ? (
        <PanelEmpty title="No cases to diagnose">
          No stored event log, or the active filter excludes every case. Mine a log or relax the
          filter.
        </PanelEmpty>
      ) : !report ? (
        <PanelLoader />
      ) : (
        <RootCauseBody report={report} />
      )}
    </div>
  );
}

function RootCauseBody({ report }: { report: RootCauseReport }) {
  const maxImpact = Math.max(...report.factors.map((f) => f.impact_score), 1);

  return (
    <div className="space-y-4">
      <p className="text-xs text-slate-500">
        Slow = case over {formatDuration(report.threshold_seconds)} (P75 cutoff).
      </p>

      <div className="grid grid-cols-3 gap-3">
        <Stat label="Slow cases" value={`${report.bad_cases}/${report.total_cases}`} />
        <Stat label="Baseline rate" value={`${Math.round(report.baseline_rate * 100)}%`} />
        <Stat label="Factors" value={`${report.factors.length}`} />
      </div>

      {report.factors.length === 0 ? (
        <div className="glass p-5 text-sm text-slate-400">
          <p className="font-medium text-slate-200">No dominant factor</p>
          <p className="mt-1">
            Slowness is spread evenly — no attribute is over-represented among the slow cases.
          </p>
        </div>
      ) : (
        <ul className="space-y-2">
          {report.factors.map((f) => {
            const Icon = DIMENSION_ICON[f.dimension];
            const label = f.factor.includes('=')
              ? f.factor.split('=').slice(1).join('=')
              : f.factor;
            const tone =
              f.lift >= 2
                ? 'text-sev-critical'
                : f.lift >= 1.5
                  ? 'text-sev-high'
                  : 'text-sev-medium';
            return (
              <li key={f.factor} className="glass p-3.5">
                <div className="mb-1.5 flex items-center justify-between gap-2">
                  <div className="flex min-w-0 items-center gap-2">
                    <span className="grid h-6 w-6 shrink-0 place-items-center rounded-md bg-white/5 text-slate-400">
                      <Icon size={13} aria-hidden="true" />
                    </span>
                    <span className="truncate text-sm font-medium text-slate-100">{label}</span>
                    <span className="chip shrink-0 bg-white/5 text-[10px] uppercase text-slate-500">
                      {f.dimension}
                    </span>
                  </div>
                  <span className={cn('number shrink-0 text-sm font-semibold', tone)}>
                    {f.lift.toFixed(1)}× lift
                  </span>
                </div>
                <div className="mb-1.5 h-1.5 overflow-hidden rounded-full bg-white/5">
                  <div
                    className="h-full rounded-full bg-accent-deep"
                    style={{ width: `${Math.max((f.impact_score / maxImpact) * 100, 3)}%` }}
                  />
                </div>
                <p className="text-[11px] text-slate-500">
                  {Math.round(f.factor_breach_rate * 100)}% of its {f.cases_with_factor} cases are
                  slow (vs {Math.round(f.baseline_rate * 100)}% baseline)
                </p>
              </li>
            );
          })}
        </ul>
      )}
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
