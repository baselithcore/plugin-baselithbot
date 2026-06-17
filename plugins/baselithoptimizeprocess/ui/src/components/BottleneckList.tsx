import { AlertOctagon, AlertTriangle, CheckCircle2, Info } from 'lucide-react';

import type { Bottleneck, Severity } from '../api/types';
import { cn, severityChip, severityColor, severityRank } from '../lib/ui';

const SEVERITY_ICON = {
  low: Info,
  medium: AlertTriangle,
  high: AlertTriangle,
  critical: AlertOctagon,
} as const;

interface BottleneckListProps {
  bottlenecks: Bottleneck[];
  /** Number of KPIs defined on the process (drives the honest empty state). */
  kpiCount?: number;
  /** Whether any KPI has ingested samples yet. */
  hasMetrics?: boolean;
}

/** Ranked list of detected bottlenecks, worst first. */
export function BottleneckList({ bottlenecks, kpiCount, hasMetrics }: BottleneckListProps) {
  const sorted = [...bottlenecks].sort(
    (a, b) => severityRank[b.severity] - severityRank[a.severity]
  );

  if (sorted.length === 0) {
    // Bottleneck detection is metric-driven: be explicit about *why* the list
    // is empty rather than implying everything is healthy.
    let heading = 'No bottlenecks detected.';
    let detail = 'All KPIs are within target.';
    if (kpiCount === 0) {
      heading = 'No KPIs defined for this process.';
      detail = 'Add a KPI with a target, then ingest metrics to detect bottlenecks.';
    } else if (hasMetrics === false) {
      heading = 'No metrics ingested yet.';
      detail =
        'Bottleneck detection needs KPI samples — feed metrics on the Live monitor tab. The Optimize tab can still suggest structural improvements.';
    }
    const healthy = kpiCount !== 0 && hasMetrics !== false;
    return (
      <div className="glass flex items-start gap-3 p-5">
        <span
          className={cn(
            'grid h-8 w-8 shrink-0 place-items-center rounded-lg',
            healthy ? 'bg-sev-low/10 text-sev-low' : 'bg-white/[0.05] text-slate-500'
          )}
        >
          {healthy ? <CheckCircle2 size={17} /> : <Info size={17} />}
        </span>
        <div>
          <p className="text-sm font-medium text-slate-300">{heading}</p>
          <p className="mt-1 text-xs text-slate-500">{detail}</p>
        </div>
      </div>
    );
  }

  return (
    <ul className="space-y-2">
      {sorted.map((b, i) => {
        const Icon = SEVERITY_ICON[b.severity as Severity];
        return (
          <li
            key={`${b.kpi_id}-${b.node_id ?? 'proc'}-${i}`}
            className="glass glass-hover flex items-start gap-3 p-4"
          >
            <Icon
              size={18}
              className="mt-0.5 shrink-0"
              style={{ color: severityColor[b.severity] }}
              aria-hidden="true"
            />
            <div className="min-w-0 flex-1">
              <span className={cn('chip mb-1.5', severityChip[b.severity])}>{b.severity}</span>
              <p className="break-words text-sm text-slate-200">{b.detail}</p>
              <p className="mt-2 flex flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-slate-500">
                KPI <span className="font-mono">{b.kpi_id}</span>
                {b.node_id && (
                  <>
                    {' · step '}
                    <span className="font-mono">{b.node_id}</span>
                  </>
                )}
              </p>
            </div>
          </li>
        );
      })}
    </ul>
  );
}
