import { Sparkles, Play, Timer, ArrowRight, TriangleAlert } from 'lucide-react';
import { useEffect, useState } from 'react';

import { api } from '../../api/client';
import type { CasePrediction, PredictorModel } from '../../api/types';
import { parseEventLog, SAMPLE_EVENT_LOG } from '../../lib/eventlog';
import { cn, formatDuration } from '../../lib/ui';
import { PanelEmpty } from './states';

/** Predictive monitoring: forecast a running case against the learned model. */
export function PredictPanel({ processId }: { processId: string }) {
  const [model, setModel] = useState<PredictorModel | null>(null);
  const [missing, setMissing] = useState(false);
  const [text, setText] = useState('');
  const [prediction, setPrediction] = useState<CasePrediction | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setModel(null);
    setMissing(false);
    void api
      .predictor(processId)
      .then((m) => (m.case_count === 0 ? setMissing(true) : setModel(m)))
      .catch(() => setMissing(true));
  }, [processId]);

  async function predict() {
    setError(null);
    setBusy(true);
    try {
      const events = parseEventLog(text);
      if (events.length === 0) throw new Error('No running-case events parsed.');
      setPrediction(await api.predictCase(processId, events));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Prediction failed');
    } finally {
      setBusy(false);
    }
  }

  if (missing) {
    return (
      <PanelEmpty title="No history to learn from">
        Predictive monitoring learns from completed cases. Mine this process from an event log
        first, then paste a running case here to forecast it.
      </PanelEmpty>
    );
  }

  return (
    <div className="space-y-5">
      <div className="flex items-center gap-2.5">
        <span className="grid h-8 w-8 place-items-center rounded-lg bg-accent/10 text-accent-soft">
          <Sparkles size={16} aria-hidden="true" />
        </span>
        <div>
          <h2 className="text-sm font-semibold text-slate-100">Predictive Monitoring</h2>
          <p className="text-sm text-slate-400">
            Forecast a running case from {model ? `${model.case_count} learned cases` : 'history'} —
            remaining time, next step, SLA risk.
          </p>
        </div>
      </div>

      <label className="block text-[11px] font-medium text-slate-400">
        Running case (events so far)
        <textarea
          className="field mt-1 min-h-[150px] font-mono text-xs"
          name="running-case-log"
          autoComplete="off"
          spellCheck={false}
          placeholder="Paste the in-flight case's events (CSV or JSON)…"
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
      </label>
      <div className="flex flex-wrap items-center gap-2">
        <button className="btn-primary" onClick={predict} disabled={busy || !text}>
          <Play size={15} aria-hidden="true" />
          {busy ? 'Predicting…' : 'Predict'}
        </button>
        <button className="btn-ghost" onClick={() => setText(SAMPLE_EVENT_LOG)}>
          Load Sample
        </button>
      </div>
      {error && (
        <p className="text-sm text-sev-critical" aria-live="polite">
          {error}
        </p>
      )}

      {prediction && <PredictionCard prediction={prediction} />}
      {model && <ModelCard model={model} />}
    </div>
  );
}

function PredictionCard({ prediction }: { prediction: CasePrediction }) {
  return (
    <div className="glass space-y-3 p-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-sm text-slate-300">
          Case <span className="font-mono text-slate-100">{prediction.case_id}</span> at{' '}
          <span className="chip bg-accent/10 text-accent-soft">{prediction.current_activity}</span>
        </span>
        <span className="text-[11px] text-slate-500">
          confidence {Math.round(prediction.confidence * 100)}%
        </span>
      </div>

      {prediction.completed ? (
        <p className="text-sm text-sev-low">
          Case is at a terminal step — nothing left to predict.
        </p>
      ) : (
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          <Metric label="Elapsed" value={formatDuration(prediction.elapsed_seconds)} />
          <Metric
            label="Remaining ~"
            value={formatDuration(prediction.predicted_remaining_seconds)}
            icon={<Timer size={13} aria-hidden="true" />}
          />
          <Metric
            label="Remaining p90"
            value={formatDuration(prediction.predicted_remaining_p90_seconds)}
          />
          <Metric
            label="Projected total"
            value={formatDuration(prediction.predicted_total_seconds)}
          />
        </div>
      )}

      {prediction.next_activities.length > 0 && (
        <div>
          <p className="mb-1 text-[11px] font-semibold uppercase tracking-wide text-slate-400">
            Likely next step
          </p>
          <div className="flex flex-wrap gap-1.5">
            {prediction.next_activities.map((n) => (
              <span key={n.activity} className="chip bg-white/5 text-slate-300">
                <ArrowRight size={11} aria-hidden="true" /> {n.activity} ·{' '}
                {Math.round(n.probability * 100)}%
              </span>
            ))}
          </div>
        </div>
      )}

      {prediction.slas.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {prediction.slas.map((s) => (
            <span
              key={s.sla_id}
              className={cn(
                'chip',
                s.will_breach
                  ? 'bg-sev-critical/12 text-sev-critical'
                  : 'bg-sev-low/12 text-sev-low'
              )}
            >
              {s.will_breach && <TriangleAlert size={11} aria-hidden="true" />}
              {s.name}: {Math.round(s.violation_probability * 100)}% breach risk
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function ModelCard({ model }: { model: PredictorModel }) {
  return (
    <details className="glass p-3">
      <summary className="cursor-pointer text-xs font-semibold text-slate-300">
        Predictor model card · {model.states.length} states
      </summary>
      <div className="mt-2 divide-y divide-white/5">
        {model.states.map((s) => (
          <div key={s.activity} className="flex items-center justify-between gap-3 py-1.5 text-sm">
            <span className="min-w-0 truncate text-slate-200">
              {s.activity}
              {s.is_terminal && <span className="ml-1 text-[10px] text-slate-500">(end)</span>}
            </span>
            <span className="shrink-0 text-xs text-slate-500">
              {s.observations}× · rem p50 {formatDuration(s.remaining.p50)}
              {s.next_activities[0] && ` · →${s.next_activities[0].activity}`}
            </span>
          </div>
        ))}
      </div>
    </details>
  );
}

function Metric({ label, value, icon }: { label: string; value: string; icon?: React.ReactNode }) {
  return (
    <div className="metric-card">
      <p className="flex items-center gap-1 text-[11px] uppercase tracking-wide text-slate-500">
        {icon}
        {label}
      </p>
      <p className="number mt-1 text-base font-semibold text-slate-100">{value}</p>
    </div>
  );
}
