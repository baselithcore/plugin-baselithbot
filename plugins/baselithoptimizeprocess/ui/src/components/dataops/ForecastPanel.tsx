import { useEffect, useState } from 'react';

import { api } from '../../api/client';
import type { Anomaly, BreachForecast } from '../../api/types';

/** Predictive view: breach forecasts + recent statistical anomalies. */
export function ForecastPanel({ processId }: { processId: string }) {
  const [forecasts, setForecasts] = useState<BreachForecast[]>([]);
  const [anomalies, setAnomalies] = useState<Anomaly[]>([]);

  useEffect(() => {
    let live = true;
    api
      .forecast(processId)
      .then((f) => live && setForecasts(f))
      .catch(() => undefined);
    api
      .anomalies(processId)
      .then((a) => live && setAnomalies(a))
      .catch(() => undefined);
    return () => {
      live = false;
    };
  }, [processId]);

  const breaching = forecasts.filter((f) => f.will_breach);

  if (breaching.length === 0 && anomalies.length === 0) {
    return (
      <div className="glass p-4 text-sm text-slate-500">
        <p className="font-medium text-slate-300">No predictive alerts</p>
        <p className="mt-1 text-xs">
          Forecasts need a trend of KPI samples before they can detect breaches or anomalies.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {breaching.length > 0 && (
        <div className="glass p-3">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-sev-medium">
            Forecast Breaches
          </p>
          <ul className="space-y-1.5">
            {breaching.map((f) => (
              <li key={f.kpi_id} className="flex items-center justify-between text-sm">
                <span className="font-mono text-slate-300">{f.kpi_id}</span>
                <span className="text-sev-medium">
                  {f.samples_to_breach ? `breach in ~${f.samples_to_breach} samples` : 'breaching'}
                  <span className="ml-1 text-[11px] text-slate-500">
                    → {f.projected_value} vs {f.target}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {anomalies.length > 0 && (
        <div className="glass p-3">
          <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-sev-high">
            Anomalies ({anomalies.length})
          </p>
          <ul className="space-y-1.5">
            {anomalies.slice(0, 8).map((a, i) => (
              <li key={i} className="flex items-center justify-between text-sm">
                <span className="font-mono text-slate-300">{a.kpi_id}</span>
                <span className="text-slate-400">
                  {a.value}{' '}
                  <span className="text-[11px] text-slate-500">
                    (z {a.z_score}, exp {a.expected})
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
