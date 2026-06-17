import { FileSearch, Play, ShieldCheck } from 'lucide-react';
import { useState } from 'react';

import { api } from '../../api/client';
import type { ConformanceReport } from '../../api/types';
import { parseEventLog, SAMPLE_EVENT_LOG } from '../../lib/eventlog';
import { cn, formatNumber } from '../../lib/ui';

/** Score an event log against the mapped model and surface deviations. */
export function ConformancePanel({ processId }: { processId: string }) {
  const [text, setText] = useState('');
  const [report, setReport] = useState<ConformanceReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function check() {
    setError(null);
    setBusy(true);
    try {
      const events = parseEventLog(text);
      if (events.length === 0) throw new Error('No events parsed.');
      setReport(await api.checkConformance(processId, events));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Conformance check failed');
    } finally {
      setBusy(false);
    }
  }

  const pct = report ? Math.round(report.fitness * 100) : 0;
  const tone = pct >= 90 ? 'text-sev-low' : pct >= 70 ? 'text-sev-medium' : 'text-sev-critical';

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2.5">
        <span className="grid h-8 w-8 place-items-center rounded-lg bg-accent/10 text-accent-soft">
          <ShieldCheck size={16} aria-hidden="true" />
        </span>
        <div>
          <h2 className="text-sm font-semibold text-slate-100">Conformance Check</h2>
          <p className="text-sm text-slate-400">
            Measure how faithfully reality follows this model.
          </p>
        </div>
      </div>
      <label className="block text-[11px] font-medium text-slate-400">
        Event Log
        <textarea
          className="field mt-1 min-h-[190px] font-mono text-xs"
          name="conformance-event-log"
          autoComplete="off"
          spellCheck={false}
          placeholder="Paste CSV or JSON event data…"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
      </label>
      <div className="flex flex-wrap items-center gap-2">
        <button className="btn-primary" onClick={check} disabled={busy || !text}>
          <Play size={15} aria-hidden="true" />
          {busy ? 'Checking…' : 'Check Conformance'}
        </button>
        <button className="btn-ghost" onClick={() => setText(SAMPLE_EVENT_LOG)}>
          <FileSearch size={15} aria-hidden="true" />
          Load Sample Log
        </button>
      </div>
      {error && (
        <p className="text-sm text-sev-critical" aria-live="polite">
          {error}
        </p>
      )}

      {report && (
        <div className="space-y-3">
          <div className="glass grid grid-cols-1 gap-4 p-4 md:grid-cols-3">
            <div className="flex items-center gap-3">
              <div className={cn('number text-4xl font-bold', tone)}>{pct}%</div>
              <div className="text-sm">
                <p className="font-medium text-slate-200">Fitness</p>
                <p className="text-[11px] text-slate-500">How often reality matches the model</p>
                <p className="mt-0.5 text-[11px] text-slate-500">
                  {report.conforming_cases} on-model · {report.deviating_cases} deviated
                </p>
              </div>
            </div>
            <div className="text-sm">
              <p className="text-[11px] font-medium uppercase tracking-wide text-slate-400">
                Alignment
              </p>
              <p className="number text-xl font-semibold text-accent-soft">
                {Math.round(report.alignment_fitness * 100)}%
              </p>
              <p className="text-[11px] text-slate-500">
                Closeness allowing partial matches (avg case{' '}
                {Math.round(report.avg_case_fitness * 100)}%)
              </p>
            </div>
            {report.deviation_cost > 0 && (
              <div className="text-sm">
                <p className="text-[11px] font-medium uppercase tracking-wide text-slate-400">
                  Deviation cost
                </p>
                <p className="number text-xl font-semibold text-sev-medium">
                  {formatNumber(report.deviation_cost)} {report.currency}
                </p>
                <p className="text-[11px] text-slate-500">Estimated cost of off-model steps</p>
              </div>
            )}
          </div>

          {report.undesired_transitions.length > 0 && (
            <div className="glass p-3">
              <p className="mb-0.5 text-xs font-semibold uppercase tracking-wide text-slate-400">
                Unexpected transitions
              </p>
              <p className="mb-2 text-[11px] text-slate-500">
                Step-to-step moves in the log that the model doesn’t allow.
              </p>
              <ul className="space-y-1 text-sm">
                {report.undesired_transitions.map((d, i) => (
                  <li key={i} className="flex items-center justify-between">
                    <span className="font-mono text-slate-300">
                      {d.source} → {d.target}
                    </span>
                    <span className="text-xs text-sev-critical">{d.count}×</span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {report.unseen_activities.length > 0 && (
            <div className="glass p-3">
              <p className="mb-0.5 text-xs font-semibold uppercase tracking-wide text-slate-400">
                Modelled but never observed
              </p>
              <p className="mb-2 text-[11px] text-slate-500">
                Steps in your model that the real log never shows.
              </p>
              <div className="flex flex-wrap gap-1">
                {report.unseen_activities.map((a) => (
                  <span key={a} className="chip bg-white/5 text-slate-400">
                    {a}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
