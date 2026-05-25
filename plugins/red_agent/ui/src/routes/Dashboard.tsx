import { useMemo, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Link, useNavigate } from 'react-router-dom';
import { api, type Finding, type Severity, type ScanRow, type TargetRecord } from '../lib/api';
import { Button, Card, Icon, MetricAreaChart, PageHeader, Sparkline } from '../components/ui';
import { TopIssuesCard } from './dashboard/TopIssuesCard';
import { PostureRow, deriveMTTR } from './dashboard/PostureRow';
import { LiveOps } from './dashboard/LiveOps';
import { ActivityFeed } from './dashboard/ActivityFeed';
import { CoverageCard } from './dashboard/CoverageCard';
import { SEVERITY_ORDER, fmtDate } from './dashboard/_utils';

export function Dashboard() {
  const [target, setTarget] = useState('');
  const navigate = useNavigate();

  const start = useMutation({
    mutationFn: api.quickScan,
    onSuccess: (data) => navigate(`/scans/${data.scan_id}`),
  });

  const findings = useQuery({
    queryKey: ['findings', 'dashboard'],
    queryFn: () => api.listFindings({ limit: 500 }),
    refetchInterval: 15000,
  });
  const scans = useQuery({
    queryKey: ['scans', 'dashboard'],
    queryFn: () => api.listScans({ limit: 100 }),
    refetchInterval: 5000,
  });
  const targets = useQuery({
    queryKey: ['targets', 'dashboard'],
    queryFn: () => api.listTargets({ limit: 250 }),
    refetchInterval: 30000,
  });

  const f: Finding[] = findings.data ?? [];
  const s: ScanRow[] = scans.data ?? [];
  const t: TargetRecord[] = targets.data ?? [];

  const sevCounts = useMemo<Record<Severity, number>>(() => {
    const c: Record<Severity, number> = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
    for (const x of f) if (x.state === 'open') c[x.severity]++;
    return c;
  }, [f]);

  const totalIssues =
    sevCounts.critical + sevCounts.high + sevCounts.medium + sevCounts.low + sevCounts.info;

  const last24h = useMemo(() => {
    const cutoff = Date.now() - 24 * 3600 * 1000;
    return s.filter((x) => new Date(x.started_at).getTime() >= cutoff).length;
  }, [s]);

  const running = s.filter((x) => x.status === 'running' || x.status === 'queued').length;
  const awaitingApproval = s.filter((x) => x.status === 'awaiting_approval').length;
  const failedScans = s.filter((x) => x.status === 'failed').length;

  const targetsCovered = useMemo(() => new Set(f.map((x) => x.target)).size, [f]);
  const totalTargets = t.length || targetsCovered;
  const targetCoverage = totalTargets > 0 ? Math.round((targetsCovered / totalTargets) * 100) : 0;

  const overdueFindings = useMemo(
    () =>
      f.filter((x) => x.state === 'open' && x.due_at && new Date(x.due_at).getTime() < Date.now()),
    [f]
  );
  const dueSoonFindings = useMemo(
    () =>
      f.filter((x) => {
        if (x.state !== 'open' || !x.due_at) return false;
        const due = new Date(x.due_at).getTime();
        return due >= Date.now() && due <= Date.now() + 7 * 24 * 3600 * 1000;
      }),
    [f]
  );
  const exploitableSignals = useMemo(
    () =>
      f.filter((x) => {
        if (x.state !== 'open') return false;
        const haystack =
          `${x.cve ?? ''} ${x.cwe ?? ''} ${x.title} ${x.description ?? ''}`.toLowerCase();
        return (
          x.severity === 'critical' ||
          (x.cvss_score !== null && x.cvss_score >= 9) ||
          haystack.includes('kev') ||
          haystack.includes('known exploited') ||
          haystack.includes('exploit')
        );
      }),
    [f]
  );
  const untriaged = f.filter((x) => x.state === 'open' && !x.assignee).length;
  const triaged = f.filter((x) => x.state !== 'open' || x.assignee).length;
  const triageCoverage = f.length > 0 ? Math.round((triaged / f.length) * 100) : 100;

  const { mttrHours, mtttHours } = useMemo(() => deriveMTTR(f), [f]);

  // 30-day trend by severity
  const trend = useMemo(() => {
    const days = 30;
    const xLabels: string[] = [];
    const critical: number[] = [];
    const high: number[] = [];
    const now = new Date();
    for (let i = days - 1; i >= 0; i--) {
      const d = new Date(now);
      d.setDate(now.getDate() - i);
      xLabels.push(fmtDate(d));
      const key = d.toISOString().slice(0, 10);
      let c = 0;
      let h = 0;
      for (const x of f) {
        if (x.discovered_at.slice(0, 10) === key) {
          if (x.severity === 'critical') c++;
          else if (x.severity === 'high') h++;
        }
      }
      critical.push(c);
      high.push(h);
    }
    return { xLabels, critical, high };
  }, [f]);

  // 7-day scan throughput
  const scanThroughput = useMemo(() => {
    const days = 7;
    const xLabels: string[] = [];
    const counts: number[] = [];
    const now = new Date();
    for (let i = days - 1; i >= 0; i--) {
      const d = new Date(now);
      d.setDate(now.getDate() - i);
      xLabels.push(fmtDate(d));
      const key = d.toISOString().slice(0, 10);
      counts.push(s.filter((x) => x.started_at.slice(0, 10) === key).length);
    }
    return { xLabels, counts };
  }, [s]);

  const findingsLast7 = useMemo(() => {
    const days = 7;
    const out: number[] = [];
    const now = new Date();
    for (let i = days - 1; i >= 0; i--) {
      const d = new Date(now);
      d.setDate(now.getDate() - i);
      const key = d.toISOString().slice(0, 10);
      out.push(f.filter((x) => x.discovered_at.slice(0, 10) === key).length);
    }
    return out;
  }, [f]);

  const readinessScore = useMemo(() => {
    if (totalIssues === 0 && s.length === 0) return 100;
    const weighted =
      sevCounts.critical * 8 + sevCounts.high * 4 + sevCounts.medium * 1.5 + sevCounts.low * 0.4;
    const failedShare =
      s.length > 0 ? (s.filter((x) => x.status === 'failed').length / s.length) * 30 : 0;
    const slaPressure = overdueFindings.length * 3 + dueSoonFindings.length;
    const triageGap = Math.max(0, 100 - triageCoverage) * 0.18;
    const coverageGap = Math.max(0, 100 - targetCoverage) * 0.12;
    return Math.max(
      0,
      Math.min(
        100,
        Math.round(100 - weighted - failedShare - slaPressure - triageGap - coverageGap)
      )
    );
  }, [
    sevCounts,
    totalIssues,
    s,
    overdueFindings.length,
    dueSoonFindings.length,
    triageCoverage,
    targetCoverage,
  ]);

  const topFindings = useMemo(
    () =>
      [...f]
        .filter((x) => x.state === 'open')
        .sort((a, b) => {
          const ai = SEVERITY_ORDER.indexOf(a.severity);
          const bi = SEVERITY_ORDER.indexOf(b.severity);
          if (ai !== bi) return ai - bi;
          return (b.cvss_score ?? 0) - (a.cvss_score ?? 0);
        })
        .slice(0, 7),
    [f]
  );

  const actionQueue = [
    {
      label: 'Critical exposure',
      value: sevCounts.critical + sevCounts.high,
      detail: `${exploitableSignals.length} exploitable`,
      tone: sevCounts.critical > 0 ? 'critical' : sevCounts.high > 0 ? 'warn' : 'good',
      icon: <Icon.Bug size={14} />,
      to: '/findings?severity=critical',
    },
    {
      label: 'SLA overdue',
      value: overdueFindings.length,
      detail: `${dueSoonFindings.length} due ≤7d`,
      tone: overdueFindings.length > 0 ? 'critical' : 'good',
      icon: <Icon.Clock size={14} />,
      to: '/findings?overdue=true',
    },
    {
      label: 'Awaiting approval',
      value: awaitingApproval,
      detail: 'gated operations',
      tone: awaitingApproval > 0 ? 'warn' : 'good',
      icon: <Icon.Shield size={14} />,
      to: '/approvals',
    },
    {
      label: 'Coverage gap',
      value: Math.max(0, totalTargets - targetsCovered),
      detail: `${targetCoverage}% scanned`,
      tone: targetCoverage < 70 ? 'warn' : 'good',
      icon: <Icon.Target size={14} />,
      to: '/targets',
    },
  ] as const;

  return (
    <div className="space-y-5">
      <PageHeader
        title="Red team"
        breadcrumbs={[{ label: 'Workspace' }, { label: 'Dashboard' }]}
        badge={{ label: 'Live', tone: 'live' }}
        actions={
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="md" onClick={() => findings.refetch()}>
              <Icon.Refresh size={14} />
              Refresh
            </Button>
            <Link to="/scans/new" className="ra-btn ra-btn-primary ra-btn-md">
              <Icon.Scans size={14} />
              New scan
            </Link>
          </div>
        }
      />

      {/* Quick launch — compact, single row */}
      <section className="rounded-lg border border-bg-line bg-bg-card animate-enter-up">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (target) start.mutate(target);
          }}
          className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:gap-3"
        >
          <div className="flex shrink-0 items-center gap-2 font-mono text-2xs uppercase tracking-wider text-text-muted">
            <span className="grid h-7 w-7 place-items-center rounded bg-brand/10 text-brand">
              <Icon.Activity size={13} />
            </span>
            Quick scan
          </div>
          <input
            type="url"
            required
            placeholder="https://api.example.com"
            value={target}
            onChange={(e) => setTarget(e.target.value)}
            className="ra-input h-10 flex-1 font-mono text-sm"
          />
          <button
            type="submit"
            disabled={start.isPending}
            className="ra-btn ra-btn-primary h-10 px-5"
          >
            {start.isPending ? 'Launching…' : 'Run passive'}
            <Icon.ArrowRight size={14} />
          </button>
          <span className="font-mono text-2xs text-text-subtle">active runs require approval</span>
        </form>
        {start.error && (
          <p className="border-t border-sev-critical/40 bg-sev-critical/10 px-4 py-2 text-sm text-sev-critical">
            Error: {String(start.error)}
          </p>
        )}
      </section>

      {/* Posture row — gauge + severity stack + SLA pressure */}
      <div className="animate-enter-up [animation-delay:60ms]">
        <PostureRow
          readinessScore={readinessScore}
          benchmark={75}
          sevCounts={sevCounts}
          totalIssues={totalIssues}
          mttrHours={mttrHours}
          meanTimeToTriageHours={mtttHours}
          overdueCount={overdueFindings.length}
          dueSoonCount={dueSoonFindings.length}
          triageCoverage={triageCoverage}
          untriaged={untriaged}
        />
      </div>

      {/* Action queue — 4 navigable tiles */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 animate-enter-up [animation-delay:120ms]">
        {actionQueue.map((item) => (
          <Link
            key={item.label}
            to={item.to}
            className="ra-card ra-card-hover group flex items-center gap-3 px-4 py-3 transition-transform duration-200 hover:-translate-y-0.5"
          >
            <span
              className={`grid h-9 w-9 place-items-center rounded ${
                item.tone === 'critical'
                  ? 'bg-sev-critical/10 text-sev-critical'
                  : item.tone === 'warn'
                    ? 'bg-accent-warn/10 text-accent-warn'
                    : 'bg-status-success/10 text-status-success'
              }`}
            >
              {item.icon}
            </span>
            <div className="min-w-0 flex-1">
              <p className="ra-section-title">{item.label}</p>
              <div className="mt-0.5 flex items-baseline gap-2">
                <span
                  className={`font-display text-2xl font-medium tabular-nums ${
                    item.tone === 'critical'
                      ? 'text-sev-critical'
                      : item.tone === 'warn'
                        ? 'text-accent-warn'
                        : 'text-status-success'
                  }`}
                >
                  {item.value}
                </span>
                <span className="text-2xs text-text-muted">{item.detail}</span>
              </div>
            </div>
            <Icon.ArrowRight
              size={14}
              className="shrink-0 text-text-subtle transition-colors group-hover:text-text-primary"
            />
          </Link>
        ))}
      </div>

      {/* Live Ops + Activity Feed */}
      <div className="grid gap-4 lg:grid-cols-2 animate-enter-up [animation-delay:180ms]">
        <LiveOps scans={s} />
        <ActivityFeed />
      </div>

      {/* Trend strip — open issues 30d + scan throughput 7d + KPI sparks */}
      <div className="grid gap-4 lg:grid-cols-[1.6fr_1fr] animate-enter-up [animation-delay:240ms]">
        <Card title="Open issues" subtitle="Critical & high · last 30 days" menu>
          <MetricAreaChart
            xLabels={trend.xLabels}
            series={[
              { name: 'Critical', data: trend.critical, color: '#c1485e' },
              { name: 'High', data: trend.high, color: '#d97a3a' },
            ]}
            height={200}
          />
        </Card>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-1">
          <SparkTile
            label="Scans / 7d"
            value={scanThroughput.counts.reduce((a, b) => a + b, 0)}
            hint={`${last24h} in last 24h · ${running} running`}
            series={scanThroughput.counts}
            color="#33dcff"
          />
          <SparkTile
            label="New findings / 7d"
            value={findingsLast7.reduce((a, b) => a + b, 0)}
            hint={`${failedScans} failed scans · ${untriaged} unassigned`}
            series={findingsLast7}
            color="#d97a3a"
            tone={failedScans > 0 ? 'warn' : 'neutral'}
          />
        </div>
      </div>

      {/* Top issues + Coverage */}
      <div className="grid gap-4 lg:grid-cols-[1.6fr_1fr] animate-enter-up [animation-delay:300ms]">
        <TopIssuesCard topFindings={topFindings} totalFindings={f.length} />
        <CoverageCard targets={t} findings={f} />
      </div>
    </div>
  );
}

interface SparkTileProps {
  label: string;
  value: number | string;
  hint: string;
  series: number[];
  color: string;
  tone?: 'neutral' | 'warn' | 'critical';
}

const SPARK_TONE: Record<NonNullable<SparkTileProps['tone']>, string> = {
  neutral: 'text-text-primary',
  warn: 'text-accent-warn',
  critical: 'text-sev-critical',
};

function SparkTile({ label, value, hint, series, color, tone = 'neutral' }: SparkTileProps) {
  return (
    <div className="ra-card flex flex-col p-4">
      <p className="ra-section-title">{label}</p>
      <div className="mt-2 flex items-baseline justify-between gap-3">
        <span className={`font-display text-3xl font-medium tabular-nums ${SPARK_TONE[tone]}`}>
          {value}
        </span>
      </div>
      <p className="mt-0.5 text-2xs text-text-muted">{hint}</p>
      <div className="mt-2">
        <Sparkline data={series} color={color} height={42} />
      </div>
    </div>
  );
}

export function GovernanceTrendCard({ engagementId }: { engagementId?: string } = {}) {
  const [bucket, setBucket] = useState<'minute' | 'hour' | 'day'>('hour');
  const sinceHours = bucket === 'minute' ? 4 : bucket === 'day' ? 24 * 14 : 24;
  const q = useQuery({
    queryKey: ['governance-trend', bucket, engagementId ?? 'global'],
    queryFn: () => api.governanceTrend({ sinceHours, bucket, engagementId }),
    refetchInterval: 30_000,
  });
  const series = q.data?.series ?? [];
  const points = bucket === 'day' ? 14 : bucket === 'minute' ? 60 * 4 : 24;
  const filled = fillBuckets(series, points, bucket);
  const xLabels = filled.map((p) =>
    bucket === 'day'
      ? new Date(p.ts).toLocaleDateString([], { month: 'short', day: '2-digit' })
      : bucket === 'minute'
        ? new Date(p.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
        : new Date(p.ts).toLocaleTimeString([], { hour: '2-digit' })
  );
  const total = filled.reduce((acc, p) => acc + p.violations + p.adjustments + p.hitl_timeouts, 0);
  const subtitle =
    bucket === 'day'
      ? 'Daily buckets · last 14 days'
      : bucket === 'minute'
        ? 'Minute buckets · last 4 hours'
        : 'Hourly buckets · last 24 hours';
  return (
    <Card
      title="Governance trend"
      subtitle={subtitle}
      menu
      action={
        <div className="flex gap-1 rounded border border-bg-line bg-bg-overlay p-0.5 text-2xs font-mono uppercase">
          {(['minute', 'hour', 'day'] as const).map((b) => (
            <button
              key={b}
              type="button"
              onClick={() => setBucket(b)}
              className={`rounded px-2 py-1 transition-colors ${
                bucket === b ? 'bg-brand/15 text-brand' : 'text-text-muted hover:text-text-primary'
              }`}
            >
              {b}
            </button>
          ))}
        </div>
      }
    >
      {total === 0 ? (
        <div className="grid h-40 place-items-center text-sm text-text-muted">
          <span className="font-mono">No governance events in window.</span>
        </div>
      ) : (
        <MetricAreaChart
          xLabels={xLabels}
          series={[
            {
              name: 'Violations',
              data: filled.map((p) => p.violations),
              color: '#ff3860',
            },
            {
              name: 'Adjustments',
              data: filled.map((p) => p.adjustments),
              color: '#fb7c1d',
            },
            {
              name: 'HITL timeouts',
              data: filled.map((p) => p.hitl_timeouts),
              color: '#33dcff',
            },
          ]}
          height={200}
        />
      )}
    </Card>
  );
}

function fillBuckets(
  series: { ts: string; violations: number; adjustments: number; hitl_timeouts: number }[],
  points: number,
  bucket: 'minute' | 'hour' | 'day'
): { ts: string; violations: number; adjustments: number; hitl_timeouts: number }[] {
  const stepMs = bucket === 'day' ? 86_400_000 : bucket === 'minute' ? 60_000 : 3_600_000;
  const truncate = (d: Date) => {
    const out = new Date(d);
    if (bucket === 'minute') out.setSeconds(0, 0);
    else if (bucket === 'hour') out.setMinutes(0, 0, 0);
    else out.setHours(0, 0, 0, 0);
    return out;
  };
  const map = new Map<string, (typeof series)[number]>();
  for (const p of series) {
    map.set(truncate(new Date(p.ts)).toISOString(), p);
  }
  const out: typeof series = [];
  const anchor = truncate(new Date());
  for (let i = points - 1; i >= 0; i--) {
    const d = new Date(anchor.getTime() - i * stepMs);
    const k = d.toISOString();
    out.push(map.get(k) ?? { ts: k, violations: 0, adjustments: 0, hitl_timeouts: 0 });
  }
  return out;
}
