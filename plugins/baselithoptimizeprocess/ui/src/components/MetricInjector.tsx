import { Beaker, Send } from 'lucide-react';
import { useState } from 'react';

import { api } from '../api/client';
import type { KpiDefinition, ProcessNode } from '../api/types';

interface MetricInjectorProps {
  processId: string;
  kpis: KpiDefinition[];
  nodes: ProcessNode[];
}

/**
 * Manual metric sampler — pushes a sample to the backend so operators can
 * exercise the live SSE feed, bottleneck detection, and optimizer without an
 * external metrics producer wired up.
 */
export function MetricInjector({ processId, kpis, nodes }: MetricInjectorProps) {
  const [kpiId, setKpiId] = useState(kpis[0]?.id ?? '');
  const [nodeId, setNodeId] = useState('');
  const [value, setValue] = useState('');
  const [busy, setBusy] = useState(false);

  async function send() {
    if (!kpiId || value === '') return;
    setBusy(true);
    try {
      await api.ingestMetrics(processId, [
        {
          process_id: processId,
          kpi_id: kpiId,
          value: Number(value),
          node_id: nodeId || undefined,
        },
      ]);
      setValue('');
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="glass p-4">
      <div className="mb-3 flex flex-wrap items-center gap-2.5">
        <span className="grid h-8 w-8 place-items-center rounded-lg bg-iris/10 text-iris-soft">
          <Beaker size={16} aria-hidden="true" />
        </span>
        <div>
          <h2 className="text-sm font-semibold text-slate-100">Manual Sample</h2>
          <p className="text-xs text-slate-500">
            Push a KPI sample to exercise streaming, bottleneck detection and forecasts.
          </p>
        </div>
      </div>
      <div className="grid grid-cols-1 items-end gap-3 md:grid-cols-[1fr_1fr_9rem_auto]">
        <label className="flex flex-col gap-1 text-[11px] font-medium text-slate-400">
          KPI
          <select
            className="field"
            name="metric-kpi"
            value={kpiId}
            onChange={(e) => setKpiId(e.target.value)}
            disabled={kpis.length === 0}
          >
            {kpis.map((k) => (
              <option key={k.id} value={k.id}>
                {k.name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-[11px] font-medium text-slate-400">
          Step
          <select
            className="field"
            name="metric-step"
            value={nodeId}
            onChange={(e) => setNodeId(e.target.value)}
          >
            <option value="">Process-level</option>
            {nodes.map((n) => (
              <option key={n.id} value={n.id}>
                {n.name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-[11px] font-medium text-slate-400">
          Value
          <input
            className="field"
            name="metric-value"
            type="number"
            inputMode="decimal"
            autoComplete="off"
            value={value}
            onChange={(e) => setValue(e.target.value)}
          />
        </label>
        <button className="btn-primary" onClick={send} disabled={busy || !kpiId || value === ''}>
          <Send size={15} aria-hidden="true" />
          {busy ? 'Sending…' : 'Inject Sample'}
        </button>
      </div>
    </section>
  );
}
