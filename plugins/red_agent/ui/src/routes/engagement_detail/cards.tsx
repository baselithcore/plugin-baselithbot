import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api, type ActivityEvent } from '../../lib/api';
import { Card, Chip, EmptyState, Icon } from '../../components/ui';
import { useActivityStream } from '../../hooks/useActivityStream';
import { ConnectionChip } from '../../hooks/ConnectionChip';
import { relTime } from './helpers';

const ACTIVITY_TONE: Record<string, 'neutral' | 'brand' | 'warn' | 'good' | 'critical'> = {
  'scan.roe_violation': 'critical',
  'scan.roe_adjusted': 'warn',
  'scan.critic_veto': 'critical',
  'scan.critic_amended': 'warn',
  'scan.guardrail_violation': 'critical',
  'scan.hitl_denied': 'critical',
  'scan.hitl_timeout': 'warn',
  'scan.cancel_requested': 'warn',
  'scan.cancelled': 'neutral',
};

function _activitySummary(payload: Record<string, unknown>): string {
  const rsn = payload.reason ?? payload.message ?? payload.code ?? '';
  if (typeof rsn === 'string' && rsn) return rsn;
  if (Array.isArray(payload.adjustments) && payload.adjustments.length > 0) {
    return String(payload.adjustments[0]);
  }
  return '';
}

export function EngagementActivityCard({ engagementId }: { engagementId: string }) {
  const q = useQuery({
    queryKey: ['engagement-activity', engagementId],
    queryFn: () => api.listActivity({ engagementId, cockpit: true, limit: 25 }),
    refetchInterval: 30_000,
  });
  const {
    events: live,
    connected,
    nextRetryAt,
  } = useActivityStream({
    serverEventPrefix: [
      'scan.roe_',
      'scan.critic_',
      'scan.hitl_',
      'scan.guardrail_',
      'scan.cancel',
    ],
    serverEngagementId: engagementId,
    bufferSize: 25,
  });
  const seed = q.data ?? [];
  const events: ActivityEvent[] = (() => {
    if (live.length === 0) return seed.slice(0, 25);
    const seen = new Set<number>();
    const out: ActivityEvent[] = [];
    for (const ev of [...live, ...seed]) {
      if (seen.has(ev.id)) continue;
      seen.add(ev.id);
      out.push(ev);
      if (out.length >= 25) break;
    }
    return out;
  })();
  return (
    <Card
      title="Recent governance events"
      subtitle="RoE / critic / HITL activity for this engagement"
      padded={false}
      action={<ConnectionChip connected={connected} nextRetryAt={nextRetryAt} />}
    >
      {q.isLoading ? (
        <div className="px-5 py-6 text-sm text-text-muted">Loading…</div>
      ) : events.length === 0 ? (
        <EmptyState
          compact
          icon={<Icon.Shield size={20} />}
          title="No governance events"
          description="RoE adjustments, critic vetoes, HITL events for scans in this engagement will appear here."
        />
      ) : (
        <ul className="divide-y divide-bg-line/60">
          {events.map((ev) => (
            <li key={ev.id} className="flex items-start justify-between gap-3 px-5 py-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <Chip tone={ACTIVITY_TONE[ev.event] ?? 'neutral'}>{ev.event}</Chip>
                  {ev.scan_id && (
                    <Link
                      to={`/scans/${ev.scan_id}`}
                      className="font-mono text-2xs text-text-muted hover:text-text-primary"
                    >
                      {ev.scan_id.slice(0, 8)}
                    </Link>
                  )}
                </div>
                {_activitySummary(ev.payload) && (
                  <div className="mt-1 line-clamp-2 text-xs text-text-secondary">
                    {_activitySummary(ev.payload)}
                  </div>
                )}
              </div>
              <span className="shrink-0 font-mono text-2xs text-text-muted">
                {relTime(ev.created_at)}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export function GovernanceStatsCard({ engagementId }: { engagementId: string }) {
  const q = useQuery({
    queryKey: ['engagement-governance', engagementId],
    queryFn: () => api.governanceStats({ engagementId, sinceHours: 24 }),
    refetchInterval: 30_000,
  });
  const totals = q.data?.totals ?? { violations: 0, adjustments: 0, hitl_timeouts: 0 };
  const counts = q.data?.counts ?? {};
  const breakdown: { label: string; key: string; tone: 'critical' | 'warn' | 'neutral' }[] = [
    { label: 'RoE violations', key: 'scan.roe_violation', tone: 'critical' },
    { label: 'RoE adjusted', key: 'scan.roe_adjusted', tone: 'warn' },
    { label: 'Critic veto', key: 'scan.critic_veto', tone: 'critical' },
    { label: 'Critic amended', key: 'scan.critic_amended', tone: 'warn' },
    { label: 'Guardrail block', key: 'scan.guardrail_violation', tone: 'critical' },
    { label: 'HITL denied', key: 'scan.hitl_denied', tone: 'critical' },
    { label: 'HITL timeout', key: 'scan.hitl_timeout', tone: 'warn' },
  ];
  return (
    <Card title="Governance (last 24h)" subtitle="Engagement-scoped RoE / critic / HITL events">
      <div className="grid gap-3 sm:grid-cols-3">
        <Stat label="Violations" value={totals.violations} tone="critical" />
        <Stat label="Adjustments" value={totals.adjustments} tone="warn" />
        <Stat label="HITL timeouts" value={totals.hitl_timeouts} tone="warn" />
      </div>
      <div className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-4">
        {breakdown.map((b) => (
          <div
            key={b.key}
            className="flex items-center justify-between rounded border border-bg-line/60 bg-bg-overlay px-3 py-2 text-xs"
          >
            <span className="text-text-muted">{b.label}</span>
            <Chip tone={(counts[b.key] ?? 0) > 0 ? b.tone : 'neutral'}>{counts[b.key] ?? 0}</Chip>
          </div>
        ))}
      </div>
    </Card>
  );
}

function Stat({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: 'critical' | 'warn' | 'neutral';
}) {
  const cls =
    tone === 'critical'
      ? value > 0
        ? 'border-sev-critical/40 text-sev-critical'
        : 'border-bg-line text-text-muted'
      : tone === 'warn'
        ? value > 0
          ? 'border-accent-warn/40 text-accent-warn'
          : 'border-bg-line text-text-muted'
        : 'border-bg-line text-text-primary';
  return (
    <div className={`rounded border bg-bg-overlay px-3 py-3 ${cls}`}>
      <div className="font-mono text-2xs uppercase tracking-wider opacity-70">{label}</div>
      <div className="mt-1 font-display text-2xl tabular-nums">{value}</div>
    </div>
  );
}
