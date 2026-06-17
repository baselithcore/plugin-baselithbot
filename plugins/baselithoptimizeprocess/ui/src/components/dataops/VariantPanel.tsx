import { GitBranch, Crown, TriangleAlert, GitCompare } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';

import { api } from '../../api/client';
import type { EventFilter, VariantDiff, VariantReport } from '../../api/types';
import { cn, formatDuration, formatNumber } from '../../lib/ui';
import { FilterBar } from './FilterBar';
import { PanelEmpty, PanelLoader } from './states';

/** Variant explorer: paths with share, throughput, conformance + side-by-side diff. */
export function VariantPanel({ processId }: { processId: string }) {
  const [report, setReport] = useState<VariantReport | null>(null);
  const [missing, setMissing] = useState(false);
  const [filter, setFilter] = useState<EventFilter>({});

  const load = useCallback(
    (f: EventFilter) => {
      setReport(null);
      setMissing(false);
      void api
        .variants(processId, f)
        .then((r) => (r.case_count === 0 ? setMissing(true) : setReport(r)))
        .catch(() => setMissing(true));
    },
    [processId]
  );

  useEffect(() => load(filter), [load, filter]);

  const activities = useMemo(
    () => (report ? [...new Set(report.variants.flatMap((v) => v.sequence))].sort() : []),
    [report]
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2.5">
        <span className="grid h-8 w-8 place-items-center rounded-lg bg-accent/10 text-accent-soft">
          <GitBranch size={16} aria-hidden="true" />
        </span>
        <div>
          <h2 className="text-sm font-semibold text-slate-100">Variant Explorer</h2>
          <p className="text-sm text-slate-400">
            Every distinct path, ranked by frequency. Filter and compare.
          </p>
        </div>
      </div>

      <FilterBar onApply={setFilter} activities={activities} />

      {missing ? (
        <PanelEmpty title="No cases match">
          No event log for this process, or the active filter excludes every case. Mine a log or
          relax the filter.
        </PanelEmpty>
      ) : !report ? (
        <PanelLoader />
      ) : (
        <VariantBody processId={processId} report={report} filter={filter} />
      )}
    </div>
  );
}

function VariantBody({
  processId,
  report,
  filter,
}: {
  processId: string;
  report: VariantReport;
  filter: EventFilter;
}) {
  const conformPct = report.case_count
    ? Math.round((report.conforming_cases / report.case_count) * 100)
    : 0;

  return (
    <>
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <Stat label="Cases" value={`${report.case_count}`} />
        <Stat label="Variants" value={`${report.variant_count}`} />
        <Stat label="On-model" value={`${conformPct}%`} />
        <Stat label="Rare paths" value={`${report.rare_variant_count}`} />
      </div>

      {report.variant_count >= 2 && (
        <DiffTool processId={processId} report={report} filter={filter} />
      )}

      <ul className="space-y-2">
        {report.variants.map((v) => (
          <li
            key={v.id}
            className={cn(
              'glass p-3.5',
              v.is_happy_path && 'ring-1 ring-sev-low/40',
              !v.conforms && 'ring-1 ring-sev-high/30'
            )}
          >
            <div className="mb-1.5 flex flex-wrap items-center justify-between gap-2 text-xs">
              <div className="flex items-center gap-2">
                {v.is_happy_path && (
                  <span className="chip bg-sev-low/12 text-sev-low">
                    <Crown size={12} aria-hidden="true" /> Happy path
                  </span>
                )}
                {!v.conforms && (
                  <span className="chip bg-sev-high/12 text-sev-high">
                    <TriangleAlert size={12} aria-hidden="true" /> {v.deviation_count} deviation
                    {v.deviation_count === 1 ? '' : 's'}
                  </span>
                )}
                <span className="text-slate-400">
                  {v.count} case{v.count === 1 ? '' : 's'} · {Math.round(v.share * 100)}%
                </span>
              </div>
              <div className="flex items-center gap-3 text-slate-400">
                <span title="Median / 90th-percentile throughput time">
                  {formatDuration(v.duration.p50)} · p90 {formatDuration(v.duration.p90)}
                </span>
                {v.cost_per_case > 0 && (
                  <span className="text-accent-soft">
                    {formatNumber(v.cost_per_case)} {report.currency}
                  </span>
                )}
              </div>
            </div>
            <div className="mb-2 h-1.5 overflow-hidden rounded-full bg-white/5">
              <div
                className={cn(
                  'h-full rounded-full',
                  v.is_happy_path ? 'bg-sev-low' : 'bg-accent-deep'
                )}
                style={{ width: `${Math.max(v.share * 100, 2)}%` }}
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
    </>
  );
}

function DiffTool({
  processId,
  report,
  filter,
}: {
  processId: string;
  report: VariantReport;
  filter: EventFilter;
}) {
  const def = report.variants;
  const [a, setA] = useState(report.happy_path_id ?? def[0].id);
  const [b, setB] = useState(def[1].id);
  const [diff, setDiff] = useState<VariantDiff | null>(null);

  function run() {
    setDiff(null);
    void api
      .variantDiff(processId, a, b, filter)
      .then(setDiff)
      .catch(() => setDiff(null));
  }

  const label = (id: string) => {
    const v = def.find((x) => x.id === id);
    return v ? `${v.sequence.join('→').slice(0, 40)} (${v.count})` : id;
  };

  return (
    <div className="glass p-3">
      <p className="mb-2 flex items-center gap-1.5 text-xs font-semibold text-slate-300">
        <GitCompare size={14} aria-hidden="true" /> Compare two variants
      </p>
      <div className="flex flex-wrap items-center gap-2">
        <select
          className="field w-56"
          name="variant-a"
          aria-label="Reference variant"
          value={a}
          onChange={(e) => setA(e.target.value)}
        >
          {def.map((v) => (
            <option key={v.id} value={v.id}>
              {label(v.id)}
            </option>
          ))}
        </select>
        <span className="text-slate-500">vs</span>
        <select
          className="field w-56"
          name="variant-b"
          aria-label="Comparison variant"
          value={b}
          onChange={(e) => setB(e.target.value)}
        >
          {def.map((v) => (
            <option key={v.id} value={v.id}>
              {label(v.id)}
            </option>
          ))}
        </select>
        <button className="btn-primary" onClick={run} disabled={a === b}>
          Diff
        </button>
      </div>
      {diff && (
        <div className="mt-3 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
          <Delta label="Steps added (in B)" chips={diff.added_steps} tone="text-sev-low" />
          <Delta label="Steps removed" chips={diff.removed_steps} tone="text-sev-high" />
          <div>
            <p className="text-[11px] uppercase tracking-wide text-slate-500">Δ p90 time</p>
            <p className="number mt-0.5 font-semibold text-slate-100">
              {diff.cycle_time_p90_delta >= 0 ? '+' : ''}
              {formatDuration(Math.abs(diff.cycle_time_p90_delta))}
            </p>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-wide text-slate-500">Δ cost</p>
            <p className="number mt-0.5 font-semibold text-slate-100">
              {diff.cost_delta >= 0 ? '+' : ''}
              {formatNumber(diff.cost_delta)} {diff.currency}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

function Delta({ label, chips, tone }: { label: string; chips: string[]; tone: string }) {
  return (
    <div>
      <p className="text-[11px] uppercase tracking-wide text-slate-500">{label}</p>
      <div className="mt-1 flex flex-wrap gap-1">
        {chips.length === 0 ? (
          <span className="text-xs text-slate-600">none</span>
        ) : (
          chips.map((c) => (
            <span key={c} className={cn('chip bg-white/5', tone)}>
              {c}
            </span>
          ))
        )}
      </div>
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
