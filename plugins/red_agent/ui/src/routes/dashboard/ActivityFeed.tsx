import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api, type ActivityEvent } from '../../lib/api';
import { Card, Chip, EmptyState, Icon } from '../../components/ui';
import { useActivityStream } from '../../hooks/useActivityStream';
import { ConnectionChip } from '../../hooks/ConnectionChip';
import { relTime } from './_utils';

type Tone = 'neutral' | 'brand' | 'warn' | 'good' | 'critical';

const EVENT_TONE: Record<string, Tone> = {
  'scan.roe_violation': 'critical',
  'scan.guardrail_violation': 'critical',
  'scan.critic_veto': 'critical',
  'scan.hitl_denied': 'critical',
  'scan.roe_adjusted': 'warn',
  'scan.critic_amended': 'warn',
  'scan.hitl_timeout': 'warn',
  'scan.cancel_requested': 'warn',
  'scan.cancelled': 'neutral',
  'scan.completed': 'good',
  'scan.started': 'brand',
  'scan.queued': 'neutral',
  'finding.discovered': 'warn',
  'finding.triaged': 'good',
  'finding.resolved': 'good',
};

function toneOf(name: string): Tone {
  if (EVENT_TONE[name]) return EVENT_TONE[name];
  if (name.includes('violation') || name.includes('denied')) return 'critical';
  if (name.includes('adjust') || name.includes('timeout')) return 'warn';
  if (name.includes('completed') || name.includes('resolved')) return 'good';
  return 'neutral';
}

function summary(ev: ActivityEvent): string {
  const p = ev.payload as Record<string, unknown>;
  const candidates = [p.reason, p.message, p.code, p.title, p.detail];
  for (const c of candidates) {
    if (typeof c === 'string' && c) return c;
  }
  if (Array.isArray(p.adjustments) && p.adjustments.length > 0) {
    return String(p.adjustments[0]);
  }
  return '';
}

export function ActivityFeed() {
  const seedQ = useQuery({
    queryKey: ['activity', 'dashboard'],
    queryFn: () => api.listActivity({ limit: 18 }),
    refetchInterval: 30_000,
  });
  const { events: live, connected, nextRetryAt } = useActivityStream({ bufferSize: 30 });

  const seed = seedQ.data ?? [];
  const events: ActivityEvent[] = (() => {
    if (live.length === 0) return seed.slice(0, 18);
    const seen = new Set<number>();
    const out: ActivityEvent[] = [];
    for (const ev of [...live, ...seed]) {
      if (seen.has(ev.id)) continue;
      seen.add(ev.id);
      out.push(ev);
      if (out.length >= 18) break;
    }
    return out;
  })();

  return (
    <Card
      title="Activity stream"
      subtitle="Governance · scans · findings"
      action={
        <div className="flex items-center gap-2">
          <ConnectionChip connected={connected} nextRetryAt={nextRetryAt} />
        </div>
      }
      padded={false}
    >
      {seedQ.isLoading ? (
        <FeedSkeleton />
      ) : events.length === 0 ? (
        <EmptyState
          compact
          icon={<Icon.Activity size={20} />}
          title="No activity yet"
          description="Events will stream here as scans run."
        />
      ) : (
        <ul className="max-h-[420px] divide-y divide-bg-line/60 overflow-y-auto">
          {events.map((ev) => {
            const tone = toneOf(ev.event);
            return (
              <li key={ev.id} className="flex items-start gap-3 px-5 py-2.5">
                <span
                  className={`mt-1.5 inline-block h-1.5 w-1.5 shrink-0 rounded-full ${
                    DOT_TONE[tone]
                  }`}
                  aria-hidden
                />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <Chip tone={tone}>{ev.event}</Chip>
                    {ev.scan_id && (
                      <Link
                        to={`/scans/${ev.scan_id}`}
                        className="font-mono text-2xs text-text-muted hover:text-text-primary"
                      >
                        {ev.scan_id.slice(0, 8)}
                      </Link>
                    )}
                  </div>
                  {summary(ev) && (
                    <div className="mt-1 line-clamp-2 text-xs text-text-secondary">
                      {summary(ev)}
                    </div>
                  )}
                </div>
                <span className="shrink-0 font-mono text-2xs text-text-muted">
                  {relTime(ev.created_at)}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}

const DOT_TONE: Record<Tone, string> = {
  neutral: 'bg-text-muted',
  brand: 'bg-brand',
  warn: 'bg-accent-warn',
  good: 'bg-status-success',
  critical: 'bg-sev-critical',
};

function FeedSkeleton() {
  return (
    <ul className="divide-y divide-bg-line/60">
      {Array.from({ length: 6 }).map((_, i) => (
        <li key={i} className="flex items-start gap-3 px-5 py-3">
          <div className="mt-1 h-2 w-2 rounded-full bg-bg-overlay animate-pulse" />
          <div className="min-w-0 flex-1 space-y-1.5">
            <div className="h-3 w-1/2 rounded bg-bg-overlay animate-pulse" />
            <div className="h-2.5 w-3/4 rounded bg-bg-overlay/60 animate-pulse" />
          </div>
          <div className="h-2 w-10 rounded bg-bg-overlay animate-pulse" />
        </li>
      ))}
    </ul>
  );
}
