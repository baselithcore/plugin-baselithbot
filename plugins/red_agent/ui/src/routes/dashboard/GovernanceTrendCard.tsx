import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../lib/api';
import { Card, MetricAreaChart } from '../../components/ui';

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
