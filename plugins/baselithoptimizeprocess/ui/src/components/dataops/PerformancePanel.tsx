import { Timer, Plus, Trash2, Gauge } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';

import { api } from '../../api/client';
import type {
  Distribution,
  EventFilter,
  PerformanceReport,
  SlaDefinition,
  SlaScope,
} from '../../api/types';
import { cn, formatDuration } from '../../lib/ui';
import { FilterBar } from './FilterBar';
import { PanelEmpty, PanelLoader } from './states';

/** Throughput-time percentiles, per-activity waits, and SLA breach tracking. */
export function PerformancePanel({ processId }: { processId: string }) {
  const [report, setReport] = useState<PerformanceReport | null>(null);
  const [slas, setSlas] = useState<SlaDefinition[]>([]);
  const [missing, setMissing] = useState(false);
  const [filter, setFilter] = useState<EventFilter>({});

  const refresh = useCallback(() => {
    void api
      .performance(processId, filter)
      .then((r) => (r.case_count === 0 ? setMissing(true) : setReport(r)))
      .catch(() => setMissing(true));
    void api
      .listSlas(processId)
      .then(setSlas)
      .catch(() => setSlas([]));
  }, [processId, filter]);

  useEffect(() => {
    setReport(null);
    setMissing(false);
    refresh();
  }, [refresh]);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2.5">
        <span className="grid h-8 w-8 place-items-center rounded-lg bg-accent/10 text-accent-soft">
          <Timer size={16} aria-hidden="true" />
        </span>
        <div>
          <h2 className="text-sm font-semibold text-slate-100">Performance &amp; SLA</h2>
          <p className="text-sm text-slate-400">
            Throughput-time percentiles — the tail the average hides.
          </p>
        </div>
      </div>

      <FilterBar
        onApply={setFilter}
        activities={report ? report.activities.map((a) => a.activity) : []}
      />

      {missing ? (
        <PanelEmpty title="No cases to measure">
          No stored event log, or the active filter excludes every case. Mine a log or relax the
          filter.
        </PanelEmpty>
      ) : !report ? (
        <PanelLoader />
      ) : (
        <div className="space-y-5">
          <DistributionCard title="End-to-end cycle time" dist={report.cycle_time} />

          <SlaSection
            processId={processId}
            slas={slas}
            report={report}
            activities={report.activities.map((a) => a.activity)}
            onChange={refresh}
          />

          <section>
            <h3 className="mb-2 text-sm font-semibold text-slate-200">Activity waiting time</h3>
            <div className="glass divide-y divide-white/5">
              {report.activities.map((a) => (
                <div
                  key={a.activity}
                  className="flex items-center justify-between gap-3 px-3.5 py-2"
                >
                  <span className="min-w-0 truncate text-sm text-slate-200">{a.activity}</span>
                  <span className="shrink-0 text-xs text-slate-500">
                    {a.occurrences}× · p50 {formatDuration(a.wait.p50)} · p90{' '}
                    {formatDuration(a.wait.p90)}
                  </span>
                </div>
              ))}
            </div>
          </section>
        </div>
      )}
    </div>
  );
}

function DistributionCard({ title, dist }: { title: string; dist: Distribution }) {
  const cols: [string, number][] = [
    ['P50', dist.p50],
    ['P90', dist.p90],
    ['P95', dist.p95],
    ['P99', dist.p99],
    ['Max', dist.max],
  ];
  return (
    <div className="glass p-4">
      <p className="mb-3 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
        {title}
      </p>
      <div className="grid grid-cols-3 gap-3 sm:grid-cols-5">
        {cols.map(([label, value]) => (
          <div key={label}>
            <p className="text-[11px] uppercase tracking-wide text-slate-500">{label}</p>
            <p className="number mt-0.5 text-lg font-semibold text-slate-100">
              {formatDuration(value)}
            </p>
          </div>
        ))}
      </div>
    </div>
  );
}

interface SlaSectionProps {
  processId: string;
  slas: SlaDefinition[];
  report: PerformanceReport;
  activities: string[];
  onChange: () => void;
}

function SlaSection({ processId, slas, report, activities, onChange }: SlaSectionProps) {
  const [name, setName] = useState('');
  const [scope, setScope] = useState<SlaScope>('case');
  const [activity, setActivity] = useState('');
  const [threshold, setThreshold] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const resultById = new Map(report.slas.map((r) => [r.sla_id, r]));

  async function create() {
    setError(null);
    const seconds = Number(threshold);
    if (!name.trim() || !Number.isFinite(seconds) || seconds <= 0) {
      setError('Name and a positive threshold (seconds) are required.');
      return;
    }
    if (scope === 'activity' && !activity) {
      setError('Pick a target activity for an activity-scoped SLA.');
      return;
    }
    setBusy(true);
    try {
      await api.createSla(processId, {
        name: name.trim(),
        scope,
        activity,
        threshold_seconds: seconds,
      });
      setName('');
      setThreshold('');
      onChange();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create SLA');
    } finally {
      setBusy(false);
    }
  }

  return (
    <section>
      <h3 className="mb-2 flex items-center gap-1.5 text-sm font-semibold text-slate-200">
        <Gauge size={14} aria-hidden="true" /> Service-level agreements
      </h3>

      <div className="glass mb-3 flex flex-wrap items-end gap-2 p-3">
        <label className="text-[11px] text-slate-400">
          Name
          <input
            className="field mt-1 w-44"
            name="sla-name"
            autoComplete="off"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Ship within 1 day"
          />
        </label>
        <label className="text-[11px] text-slate-400">
          Scope
          <select
            className="field mt-1 w-32"
            name="sla-scope"
            value={scope}
            onChange={(e) => setScope(e.target.value as SlaScope)}
          >
            <option value="case">Whole case</option>
            <option value="activity">Activity wait</option>
          </select>
        </label>
        {scope === 'activity' && (
          <label className="text-[11px] text-slate-400">
            Activity
            <select
              className="field mt-1 w-40"
              value={activity}
              onChange={(e) => setActivity(e.target.value)}
            >
              <option value="">Select…</option>
              {activities.map((a) => (
                <option key={a} value={a}>
                  {a}
                </option>
              ))}
            </select>
          </label>
        )}
        <label className="text-[11px] text-slate-400">
          Threshold (s)
          <input
            className="field mt-1 w-28"
            type="number"
            inputMode="numeric"
            name="sla-threshold"
            autoComplete="off"
            min={1}
            value={threshold}
            onChange={(e) => setThreshold(e.target.value)}
            placeholder="86400"
          />
        </label>
        <button className="btn-primary" onClick={create} disabled={busy}>
          <Plus size={15} aria-hidden="true" />
          {busy ? 'Adding…' : 'Add SLA'}
        </button>
      </div>
      {error && (
        <p className="mb-2 text-sm text-sev-critical" aria-live="polite">
          {error}
        </p>
      )}

      {slas.length === 0 ? (
        <p className="text-xs text-slate-500">
          No SLAs defined yet — add one above to track breach rates.
        </p>
      ) : (
        <ul className="space-y-2">
          {slas.map((sla) => {
            const r = resultById.get(sla.id);
            const pct = r ? Math.round(r.breach_rate * 100) : 0;
            const tone =
              pct === 0 ? 'text-sev-low' : pct < 25 ? 'text-sev-medium' : 'text-sev-critical';
            return (
              <li key={sla.id} className="glass flex items-center justify-between gap-3 p-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-slate-200">{sla.name}</p>
                  <p className="text-[11px] text-slate-500">
                    {sla.scope === 'activity' ? `${sla.activity} wait` : 'case'} ≤{' '}
                    {formatDuration(sla.threshold_seconds)}
                    {r &&
                      ` · ${r.breaches}/${r.observations} breached · worst ${formatDuration(r.worst_value)}`}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <span className={cn('number text-lg font-semibold', tone)}>{pct}%</span>
                  <button
                    className="btn-danger"
                    onClick={() => void api.deleteSla(sla.id).then(onChange)}
                    aria-label={`Delete SLA ${sla.name}`}
                  >
                    <Trash2 size={14} aria-hidden="true" />
                  </button>
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
