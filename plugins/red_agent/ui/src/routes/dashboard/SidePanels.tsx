import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api, type ActivityEvent, type ScanRow } from '../../lib/api';
import { Card, Chip, EmptyState, Icon, StatusBadge } from '../../components/ui';
import { useActivityStream } from '../../hooks/useActivityStream';
import { ConnectionChip } from '../../hooks/ConnectionChip';
import { KNOWN_SCANNERS, relTime } from './_utils';

const COCKPIT_PREFIXES = [
  'scan.roe_',
  'scan.critic_',
  'scan.hitl_',
  'scan.guardrail_',
  'scan.cancel',
];

function _matchesCockpitPrefix(event: string): boolean {
  return COCKPIT_PREFIXES.some((p) => event.startsWith(p));
}

const COCKPIT_TONE: Record<string, 'neutral' | 'brand' | 'warn' | 'good' | 'critical'> = {
  'scan.roe_violation': 'critical',
  'scan.roe_adjusted': 'warn',
  'scan.critic_veto': 'critical',
  'scan.critic_amended': 'warn',
  'scan.guardrail_violation': 'critical',
  'scan.hitl_timeout': 'warn',
  'scan.hitl_denied': 'critical',
  'scan.cancel_requested': 'warn',
  'scan.cancelled': 'neutral',
};

function _eventToneOf(name: string): 'neutral' | 'brand' | 'warn' | 'good' | 'critical' {
  return COCKPIT_TONE[name] ?? 'neutral';
}

function _summary(ev: ActivityEvent): string {
  const p = ev.payload as Record<string, unknown>;
  const rsn = p.reason ?? p.message ?? p.code ?? '';
  if (typeof rsn === 'string' && rsn) return rsn;
  if (Array.isArray(p.adjustments) && p.adjustments.length > 0) {
    return String(p.adjustments[0]);
  }
  return '';
}

export function CockpitActivityCard() {
  const q = useQuery({
    queryKey: ['activity', 'cockpit'],
    queryFn: () => api.listActivity({ cockpit: true, limit: 10 }),
    refetchInterval: 30_000,
  });
  const {
    events: live,
    connected,
    nextRetryAt,
  } = useActivityStream({
    serverEventPrefix: COCKPIT_PREFIXES,
    filter: (ev) => _matchesCockpitPrefix(ev.event),
    bufferSize: 20,
  });
  const seed = q.data ?? [];
  const events: ActivityEvent[] = (() => {
    if (live.length === 0) return seed.slice(0, 10);
    const seen = new Set<number>();
    const out: ActivityEvent[] = [];
    for (const ev of [...live, ...seed]) {
      if (seen.has(ev.id)) continue;
      seen.add(ev.id);
      out.push(ev);
      if (out.length >= 10) break;
    }
    return out;
  })();
  return (
    <Card
      title="RoE / critic feed"
      subtitle="Last 10 governance events"
      action={
        <div className="flex items-center gap-2">
          <ConnectionChip connected={connected} nextRetryAt={nextRetryAt} />
          <Link to="/scans" className="ra-btn ra-btn-ghost ra-btn-sm">
            View scans
            <Icon.ArrowRight size={12} />
          </Link>
        </div>
      }
      padded={false}
    >
      {q.isLoading ? (
        <div className="px-5 py-6 text-sm text-text-muted">Loading…</div>
      ) : events.length === 0 ? (
        <EmptyState
          compact
          icon={<Icon.Shield size={20} />}
          title="No governance events"
          description="RoE adjustments, critic vetoes, HITL events will appear here."
        />
      ) : (
        <ul className="divide-y divide-bg-line/60">
          {events.map((ev) => (
            <li key={ev.id} className="flex items-start justify-between gap-3 px-5 py-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <Chip tone={_eventToneOf(ev.event)}>{ev.event}</Chip>
                  {ev.scan_id && (
                    <Link
                      to={`/scans/${ev.scan_id}`}
                      className="font-mono text-2xs text-text-muted hover:text-text-primary"
                    >
                      {ev.scan_id.slice(0, 8)}
                    </Link>
                  )}
                </div>
                {_summary(ev) && (
                  <div className="mt-1 line-clamp-2 text-xs text-text-secondary">
                    {_summary(ev)}
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

export function RecentScansCard({ recentScans }: { recentScans: ScanRow[] }) {
  return (
    <Card
      title="Recent scans"
      subtitle="Last 5 launches"
      action={
        <Link to="/scans" className="ra-btn ra-btn-ghost ra-btn-sm">
          View all
          <Icon.ArrowRight size={12} />
        </Link>
      }
      padded={false}
    >
      {recentScans.length === 0 ? (
        <EmptyState
          compact
          icon={<Icon.Scans size={20} />}
          title="No scans yet"
          description="Launch your first scan to get started."
        />
      ) : (
        <ul className="divide-y divide-bg-line/60">
          {recentScans.map((sc) => (
            <li key={sc.id}>
              <Link
                to={`/scans/${sc.id}`}
                className="flex items-start justify-between gap-3 px-5 py-3 transition-colors hover:bg-bg-hover/50"
              >
                <div className="min-w-0">
                  <div className="truncate font-mono text-xs text-text-primary">
                    {sc.target_value}
                  </div>
                  <div className="mt-1 flex items-center gap-2 text-2xs text-text-muted">
                    <Icon.Clock size={11} />
                    <span>{relTime(sc.started_at)}</span>
                    <span>·</span>
                    <span className="uppercase">{sc.intensity}</span>
                  </div>
                </div>
                <StatusBadge status={sc.status} />
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

export function SensorCoverageCard({ usedScanners }: { usedScanners: Set<string> }) {
  const sensorCoverage = Math.round((usedScanners.size / KNOWN_SCANNERS.length) * 100);
  return (
    <Card
      title="Sensor coverage"
      subtitle={`${usedScanners.size} of ${KNOWN_SCANNERS.length} engines used`}
    >
      <div className="space-y-2.5">
        {KNOWN_SCANNERS.map((sc) => {
          const used = usedScanners.has(sc);
          return (
            <div key={sc} className="flex items-center gap-3">
              <div
                className={`grid h-7 w-7 place-items-center rounded text-2xs font-mono font-semibold uppercase ${
                  used
                    ? 'bg-brand/10 text-brand ring-1 ring-brand/30'
                    : 'bg-bg-overlay text-text-subtle ring-1 ring-bg-line'
                }`}
              >
                {sc.slice(0, 2)}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm text-text-primary">{sc}</div>
                <div className="mt-1 h-1 overflow-hidden rounded bg-bg-overlay">
                  <div
                    className="h-full rounded transition-all"
                    style={{
                      width: used ? '100%' : '0%',
                      background: used ? '#33dcff' : '#1f2942',
                    }}
                  />
                </div>
              </div>
              <span
                className={`text-2xs font-mono ${used ? 'text-status-success' : 'text-text-muted'}`}
              >
                {used ? 'active' : 'idle'}
              </span>
            </div>
          );
        })}
        <div className="flex items-center justify-between border-t border-bg-line/60 pt-2.5 text-xs text-text-muted">
          <span>overall coverage</span>
          <span className="font-mono tabular-nums text-text-primary">{sensorCoverage}%</span>
        </div>
      </div>
    </Card>
  );
}
