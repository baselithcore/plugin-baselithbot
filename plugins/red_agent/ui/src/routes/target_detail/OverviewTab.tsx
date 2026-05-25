import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import type { Finding, ScanRow, Severity, TargetPosture, TargetRecord } from '../../lib/api';
import {
  Card,
  Chip,
  EmptyState,
  FindingDetailModal,
  Icon,
  MetricAreaChart,
  SeverityBadge,
  StatusBadge,
} from '../../components/ui';
import { relTime } from './_utils';

export function OverviewTab({
  target,
  posture,
  findings,
  runs,
}: {
  target: TargetRecord;
  posture: TargetPosture | undefined;
  findings: Finding[];
  runs: ScanRow[];
}) {
  const [selected, setSelected] = useState<Finding | null>(null);
  const sev = posture?.severity_counts ?? {};
  const total =
    (sev.critical ?? 0) + (sev.high ?? 0) + (sev.medium ?? 0) + (sev.low ?? 0) + (sev.info ?? 0);
  const top = useMemo(
    () =>
      [...findings]
        .filter((f) => f.state === 'open' || f.state === 'triaged')
        .sort((a, b) => {
          const order: Severity[] = ['critical', 'high', 'medium', 'low', 'info'];
          return order.indexOf(a.severity) - order.indexOf(b.severity);
        })
        .slice(0, 5),
    [findings]
  );
  const trend = useMemo(() => {
    const days = 30;
    const xLabels: string[] = [];
    const critical: number[] = [];
    const high: number[] = [];
    const now = new Date();
    for (let i = days - 1; i >= 0; i--) {
      const d = new Date(now);
      d.setDate(now.getDate() - i);
      xLabels.push(d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }));
      const key = d.toISOString().slice(0, 10);
      let c = 0,
        h = 0;
      for (const x of posture?.histogram ?? []) {
        if (String(x.day).slice(0, 10) === key) {
          if (x.severity === 'critical') c += x.count;
          if (x.severity === 'high') h += x.count;
        }
      }
      critical.push(c);
      high.push(h);
    }
    return { xLabels, critical, high };
  }, [posture]);

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Stat label="Critical" value={sev.critical ?? 0} tone="critical" />
        <Stat label="High" value={sev.high ?? 0} tone="warn" />
        <Stat label="Open total" value={total} tone="brand" />
        <Stat label="Overdue (SLA)" value={posture?.overdue ?? 0} tone="critical" />
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2" title="New findings (30d)" subtitle="Critical / High">
          <MetricAreaChart
            xLabels={trend.xLabels}
            series={[
              { name: 'Critical', data: trend.critical, color: '#ff3860' },
              { name: 'High', data: trend.high, color: '#fb7c1d' },
            ]}
            height={200}
          />
        </Card>
        <Card title="Recent runs" subtitle={`${runs.length} total`} padded={false}>
          {runs.length === 0 ? (
            <EmptyState compact icon={<Icon.Scans size={20} />} title="No runs yet" />
          ) : (
            <ul className="divide-y divide-bg-line/60">
              {runs.slice(0, 6).map((r) => (
                <li key={r.id}>
                  <Link
                    to={`/scans/${r.id}`}
                    className="flex items-start justify-between gap-3 px-5 py-3 transition-colors hover:bg-bg-hover/50"
                  >
                    <div className="min-w-0">
                      <div className="font-mono text-2xs text-text-muted">
                        {r.id.slice(0, 8)} · {r.intensity}
                      </div>
                      <div className="mt-1 text-xs text-text-secondary">
                        {relTime(r.started_at)}
                      </div>
                    </div>
                    <StatusBadge status={r.status} />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
      <Card title="Top open issues" padded={false}>
        {top.length === 0 ? (
          <EmptyState
            compact
            icon={<Icon.ShieldCheck size={20} />}
            title="No open findings"
            description={`${target.name} is clean.`}
          />
        ) : (
          <table className="ra-table">
            <thead>
              <tr>
                <th className="w-24">Severity</th>
                <th>Finding</th>
                <th className="w-28">Scanner</th>
                <th className="w-28">CVE</th>
                <th className="w-24">Due</th>
              </tr>
            </thead>
            <tbody>
              {top.map((f) => (
                <tr
                  key={f.id}
                  onClick={() => setSelected(f)}
                  className="cursor-pointer transition-colors hover:bg-bg-hover/50"
                >
                  <td>
                    <SeverityBadge severity={f.severity} full />
                  </td>
                  <td>
                    <div className="font-medium text-text-primary">{f.title}</div>
                    <div className="font-mono text-xs text-text-muted">
                      {f.endpoint ?? f.target}
                    </div>
                  </td>
                  <td>
                    <Chip>{f.scanner}</Chip>
                  </td>
                  <td className="font-mono text-xs text-text-secondary">{f.cve ?? '—'}</td>
                  <td className="font-mono text-xs text-text-muted">
                    {f.due_at ? relTime(f.due_at) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
      <FindingDetailModal
        finding={selected}
        open={selected !== null}
        onClose={() => setSelected(null)}
      />
    </div>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: 'critical' | 'warn' | 'brand' | 'neutral';
}) {
  const toneCls =
    tone === 'critical'
      ? 'text-sev-critical'
      : tone === 'warn'
        ? 'text-accent-warn'
        : tone === 'brand'
          ? 'text-brand'
          : 'text-text-secondary';
  return (
    <div className="ra-card px-4 py-3">
      <div className="text-2xs font-mono uppercase tracking-wider text-text-muted">{label}</div>
      <div className={`mt-1 font-display text-2xl font-medium tabular-nums ${toneCls}`}>
        {value}
      </div>
    </div>
  );
}
