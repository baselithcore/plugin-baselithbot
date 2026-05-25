import { Link } from 'react-router-dom';
import type { Finding, Severity } from '../../lib/api';
import { Card, Icon, ReadinessGauge } from '../../components/ui';

const SEV_COLOR: Record<Severity, string> = {
  critical: '#c1485e',
  high: '#d97a3a',
  medium: '#d6a43a',
  low: '#5a8fc7',
  info: '#6e7a96',
};

interface PostureRowProps {
  readinessScore: number;
  benchmark: number;
  sevCounts: Record<Severity, number>;
  totalIssues: number;
  mttrHours: number | null;
  meanTimeToTriageHours: number | null;
  overdueCount: number;
  dueSoonCount: number;
  triageCoverage: number;
  untriaged: number;
}

export function PostureRow({
  readinessScore,
  benchmark,
  sevCounts,
  totalIssues,
  mttrHours,
  meanTimeToTriageHours,
  overdueCount,
  dueSoonCount,
  triageCoverage,
  untriaged,
}: PostureRowProps) {
  return (
    <div className="grid gap-4 lg:grid-cols-[minmax(0,360px)_minmax(0,1fr)_minmax(0,360px)]">
      <Card title="Readiness" subtitle="weighted security posture">
        <div className="flex justify-center">
          <ReadinessGauge score={readinessScore} benchmark={benchmark} height={170} />
        </div>
      </Card>

      <Card
        title="Severity distribution"
        subtitle={`${totalIssues} open findings across all targets`}
        action={
          <Link to="/findings" className="ra-btn ra-btn-ghost ra-btn-sm">
            Explore
            <Icon.ArrowRight size={12} />
          </Link>
        }
      >
        <SeverityStack counts={sevCounts} total={totalIssues} />
      </Card>

      <Card title="SLA pressure" subtitle="time-to-resolution & triage health">
        <ul className="grid grid-cols-2 gap-3">
          <PressureCell
            label="MTTR"
            value={fmtHours(mttrHours)}
            hint="mean time to fix"
            tone={mttrHours != null && mttrHours > 24 * 14 ? 'warn' : 'neutral'}
          />
          <PressureCell
            label="MTTT"
            value={fmtHours(meanTimeToTriageHours)}
            hint="mean time to triage"
            tone={meanTimeToTriageHours != null && meanTimeToTriageHours > 48 ? 'warn' : 'neutral'}
          />
          <PressureCell
            label="Overdue"
            value={overdueCount}
            hint={`${dueSoonCount} due ≤7d`}
            tone={overdueCount > 0 ? 'critical' : 'good'}
            to={overdueCount > 0 ? '/findings?overdue=true' : undefined}
          />
          <PressureCell
            label="Triage cov."
            value={`${triageCoverage}%`}
            hint={`${untriaged} unassigned`}
            tone={triageCoverage < 60 ? 'warn' : triageCoverage < 30 ? 'critical' : 'good'}
          />
        </ul>
      </Card>
    </div>
  );
}

function SeverityStack({ counts, total }: { counts: Record<Severity, number>; total: number }) {
  const order: Severity[] = ['critical', 'high', 'medium', 'low', 'info'];
  const denom = Math.max(1, total);
  return (
    <div className="space-y-3">
      <div className="flex h-2.5 w-full overflow-hidden rounded-full bg-bg-overlay">
        {order.map((s) => {
          const pct = (counts[s] / denom) * 100;
          if (pct === 0) return null;
          return (
            <div
              key={s}
              className="h-full transition-all"
              style={{ width: `${pct}%`, background: SEV_COLOR[s] }}
              title={`${s}: ${counts[s]}`}
            />
          );
        })}
      </div>
      <ul className="grid grid-cols-5 gap-2">
        {order.map((s) => (
          <li
            key={s}
            className="rounded border border-bg-line/60 bg-bg-overlay/40 px-2 py-2 text-center"
          >
            <div
              className="font-display text-2xl font-medium tabular-nums"
              style={{ color: SEV_COLOR[s] }}
            >
              {counts[s]}
            </div>
            <div className="mt-0.5 font-mono text-2xs uppercase tracking-wider text-text-muted">
              {s}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

interface CellProps {
  label: string;
  value: React.ReactNode;
  hint?: string;
  tone: 'neutral' | 'good' | 'warn' | 'critical';
  to?: string;
}

const TONE_VAL: Record<CellProps['tone'], string> = {
  neutral: 'text-text-primary',
  good: 'text-status-success',
  warn: 'text-accent-warn',
  critical: 'text-sev-critical',
};

function PressureCell({ label, value, hint, tone, to }: CellProps) {
  const body = (
    <div className="rounded border border-bg-line/60 bg-bg-overlay/40 px-3 py-3 transition-colors hover:border-bg-line-strong">
      <p className="font-mono text-2xs uppercase tracking-wider text-text-muted">{label}</p>
      <p className={`mt-1 font-display text-2xl font-medium tabular-nums ${TONE_VAL[tone]}`}>
        {value}
      </p>
      {hint && <p className="mt-0.5 truncate text-2xs text-text-muted">{hint}</p>}
    </div>
  );
  return to ? (
    <li>
      <Link to={to}>{body}</Link>
    </li>
  ) : (
    <li>{body}</li>
  );
}

function fmtHours(hours: number | null): string {
  if (hours == null || !Number.isFinite(hours)) return '—';
  if (hours < 1) return `${Math.max(1, Math.round(hours * 60))}m`;
  if (hours < 48) return `${Math.round(hours)}h`;
  return `${Math.round(hours / 24)}d`;
}

export function deriveMTTR(findings: Finding[]): {
  mttrHours: number | null;
  mtttHours: number | null;
} {
  let fixSum = 0;
  let fixN = 0;
  let triageSum = 0;
  let triageN = 0;
  for (const f of findings) {
    const disc = new Date(f.discovered_at).getTime();
    if (!Number.isFinite(disc)) continue;
    if (f.resolved_at) {
      const r = new Date(f.resolved_at).getTime();
      if (Number.isFinite(r) && r >= disc) {
        fixSum += (r - disc) / 3_600_000;
        fixN++;
      }
    }
    if (f.triaged_at) {
      const t = new Date(f.triaged_at).getTime();
      if (Number.isFinite(t) && t >= disc) {
        triageSum += (t - disc) / 3_600_000;
        triageN++;
      }
    }
  }
  return {
    mttrHours: fixN > 0 ? fixSum / fixN : null,
    mtttHours: triageN > 0 ? triageSum / triageN : null,
  };
}
