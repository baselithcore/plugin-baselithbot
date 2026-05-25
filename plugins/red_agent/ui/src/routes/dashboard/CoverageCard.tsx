import { Link } from 'react-router-dom';
import type { Finding, Severity, TargetRecord } from '../../lib/api';
import { Card, Chip, EmptyState, Icon } from '../../components/ui';

interface CoverageCardProps {
  targets: TargetRecord[];
  findings: Finding[];
}

const SEV_RANK: Record<Severity, number> = {
  critical: 5,
  high: 4,
  medium: 3,
  low: 2,
  info: 1,
};

interface Row {
  id: string;
  display: string;
  kind: string;
  total: number;
  worst: Severity | null;
  critical: number;
  high: number;
}

export function CoverageCard({ targets, findings }: CoverageCardProps) {
  const byTarget = new Map<string, Finding[]>();
  for (const f of findings) {
    const arr = byTarget.get(f.target) ?? [];
    arr.push(f);
    byTarget.set(f.target, arr);
  }

  const rows: Row[] = targets.map((t) => {
    const fs = byTarget.get(t.value) ?? byTarget.get(t.id) ?? [];
    let worst: Severity | null = null;
    for (const f of fs) {
      if (!worst || SEV_RANK[f.severity] > SEV_RANK[worst]) worst = f.severity;
    }
    return {
      id: t.id,
      display: t.value,
      kind: t.kind,
      total: fs.length,
      worst,
      critical: fs.filter((f) => f.severity === 'critical').length,
      high: fs.filter((f) => f.severity === 'high').length,
    };
  });

  rows.sort((a, b) => {
    const aw = a.worst ? SEV_RANK[a.worst] : 0;
    const bw = b.worst ? SEV_RANK[b.worst] : 0;
    if (aw !== bw) return bw - aw;
    return b.total - a.total;
  });

  const top = rows.slice(0, 8);
  const totalTargets = targets.length;
  const covered = rows.filter((r) => r.total > 0).length;
  const coverage = totalTargets > 0 ? Math.round((covered / totalTargets) * 100) : 0;

  return (
    <Card
      title="Targets at risk"
      subtitle={`${covered}/${totalTargets} scanned · ${coverage}% coverage`}
      action={
        <Link to="/targets" className="ra-btn ra-btn-ghost ra-btn-sm">
          All targets
          <Icon.ArrowRight size={12} />
        </Link>
      }
      padded={false}
    >
      {top.length === 0 ? (
        <EmptyState
          compact
          icon={<Icon.Target size={20} />}
          title="No targets registered"
          description="Add a target to start collecting findings."
        />
      ) : (
        <ul className="divide-y divide-bg-line/60">
          {top.map((row) => (
            <li key={row.id}>
              <Link
                to={`/targets/${row.id}`}
                className="flex items-center gap-3 px-5 py-2.5 transition-colors hover:bg-bg-hover/50"
              >
                <SeverityDot severity={row.worst} />
                <div className="min-w-0 flex-1">
                  <div className="truncate font-mono text-xs text-text-primary">{row.display}</div>
                  <div className="mt-0.5 flex items-center gap-2 text-2xs text-text-muted">
                    <span className="uppercase tracking-wider">{row.kind}</span>
                    {row.total > 0 ? (
                      <>
                        <span>·</span>
                        <span>{row.total} findings</span>
                      </>
                    ) : (
                      <>
                        <span>·</span>
                        <span className="text-text-subtle">no scans yet</span>
                      </>
                    )}
                  </div>
                </div>
                <div className="flex shrink-0 items-center gap-1.5">
                  {row.critical > 0 && <Chip tone="critical">C {row.critical}</Chip>}
                  {row.high > 0 && <Chip tone="warn">H {row.high}</Chip>}
                  {row.total === 0 && <Chip tone="neutral">idle</Chip>}
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

const DOT_COLOR: Record<Severity, string> = {
  critical: 'bg-sev-critical',
  high: 'bg-accent-warn',
  medium: 'bg-sev-medium',
  low: 'bg-sev-low',
  info: 'bg-sev-info',
};

function SeverityDot({ severity }: { severity: Severity | null }) {
  if (!severity) {
    return (
      <span className="inline-block h-2 w-2 rounded-full bg-text-subtle" aria-label="no findings" />
    );
  }
  return (
    <span
      className={`inline-block h-2 w-2 rounded-full ${DOT_COLOR[severity]}`}
      aria-label={`worst severity ${severity}`}
    />
  );
}
