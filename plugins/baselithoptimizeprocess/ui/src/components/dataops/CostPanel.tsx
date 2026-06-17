import { Coins } from 'lucide-react';
import { useEffect, useState } from 'react';

import { api } from '../../api/client';
import type { CostReport, SimulationResult } from '../../api/types';
import { formatNumber } from '../../lib/ui';

function money(amount: number, currency: string): string {
  return `${formatNumber(amount)} ${currency}`;
}

function fmtSecs(s: number): string {
  if (s >= 3600) return `${(s / 3600).toFixed(1)} h`;
  if (s >= 60) return `${(s / 60).toFixed(1)} min`;
  return `${s.toFixed(0)} s`;
}

/** Compact cost + cycle-time rollup for the process, when costed. */
export function CostPanel({ processId }: { processId: string }) {
  const [report, setReport] = useState<CostReport | null>(null);
  const [sim, setSim] = useState<SimulationResult | null>(null);

  useEffect(() => {
    let live = true;
    api
      .costReport(processId)
      .then((r) => live && setReport(r))
      .catch(() => live && setReport(null));
    api
      .simulate(processId)
      .then((r) => live && setSim(r))
      .catch(() => live && setSim(null));
    return () => {
      live = false;
    };
  }, [processId]);

  if (!report || report.costed_nodes === 0) {
    return (
      <div className="glass p-5 text-sm text-slate-500">
        <p className="font-medium text-slate-300">No cost data yet</p>
        <p className="mt-1">
          Add labour, handling and fixed costs to steps in{' '}
          <span className="text-accent-soft">Edit Map</span> to unlock ROI estimates.
        </p>
      </div>
    );
  }

  return (
    <section className="glass p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2.5">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-sev-low/10 text-sev-low">
            <Coins size={16} aria-hidden="true" />
          </span>
          <div>
            <h2 className="text-sm font-semibold text-slate-100">Cost Baseline</h2>
            <p className="text-xs text-slate-500">Current unit economics used by the optimizer.</p>
          </div>
        </div>
        <p className="text-[11px] text-slate-500">
          <span className="number text-slate-300">{report.costed_nodes}</span>/{report.total_nodes}{' '}
          steps costed
        </p>
      </div>
      <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
        <div>
          <p className="text-[11px] uppercase tracking-wide text-slate-500">Cost / case</p>
          <p className="number text-xl font-semibold text-accent-soft">
            {money(report.per_case_cost, report.currency)}
          </p>
        </div>
        {report.annual_cost !== null && (
          <div>
            <p className="text-[11px] uppercase tracking-wide text-slate-500">Annual cost</p>
            <p className="number text-xl font-semibold text-accent-soft">
              {money(report.annual_cost, report.currency)}
            </p>
          </div>
        )}
        {sim && sim.cycle_time_seconds > 0 && (
          <div>
            <p className="text-[11px] uppercase tracking-wide text-slate-500">Cycle time</p>
            <p className="number text-xl font-semibold text-accent-soft">
              {fmtSecs(sim.cycle_time_seconds)}
            </p>
            {sim.bottleneck_node && (
              <p className="text-[11px] text-slate-500">
                bottleneck: <span className="font-mono">{sim.bottleneck_node}</span>
              </p>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
