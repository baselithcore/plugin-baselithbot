import { Icon } from '../../components/ui';
import type { GraphSummaryStats } from './types';

export function SummaryStrip({ stats }: { stats: GraphSummaryStats }) {
  const posture =
    stats.exposureScore >= 80 ? 'critical' : stats.exposureScore >= 55 ? 'elevated' : 'managed';
  const postureClass =
    posture === 'critical'
      ? 'border-sev-critical/50 bg-sev-critical/10 text-sev-critical'
      : posture === 'elevated'
        ? 'border-accent-warn/50 bg-accent-warn/10 text-accent-warn'
        : 'border-sev-low/50 bg-sev-low/10 text-sev-low';

  return (
    <section className="grid gap-2 md:grid-cols-2 xl:grid-cols-5" aria-label="graph risk summary">
      <Metric
        icon={<Icon.Shield size={14} />}
        label="Exposure score"
        value={String(stats.exposureScore)}
        detail={posture}
        className={postureClass}
      />
      <Metric
        icon={<Icon.AlertTriangle size={14} />}
        label="Critical / high"
        value={String(stats.criticalHigh)}
        detail={`${stats.vulnerabilities} findings`}
      />
      <Metric
        icon={<Icon.Network size={14} />}
        label="Entry points"
        value={String(stats.entryPoints)}
        detail={`${stats.visibleNodes}/${stats.nodes} nodes visible`}
      />
      <Metric
        icon={<Icon.Activity size={14} />}
        label="Relations"
        value={String(stats.edges)}
        detail={`${stats.enrichments} intel links`}
      />
      <Metric
        icon={<Icon.Target size={14} />}
        label="Max CVSS"
        value={stats.maxCvss === null ? '-' : stats.maxCvss.toFixed(1)}
        detail="highest observed"
      />
    </section>
  );
}

function Metric({
  icon,
  label,
  value,
  detail,
  className = 'border-bg-line bg-bg-elevated/70 text-text-primary',
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  detail: string;
  className?: string;
}) {
  return (
    <div className={`rounded-lg border px-3 py-2 ${className}`}>
      <div className="flex items-center justify-between gap-3">
        <span className="inline-flex items-center gap-2 font-display text-[10px] uppercase tracking-wider text-text-muted">
          {icon}
          {label}
        </span>
        <span className="font-display text-lg leading-none">{value}</span>
      </div>
      <p className="mt-1 truncate text-xs text-text-muted">{detail}</p>
    </div>
  );
}
