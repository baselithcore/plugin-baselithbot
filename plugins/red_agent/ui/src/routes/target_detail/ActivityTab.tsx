import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api, type ActivityEvent } from '../../lib/api';
import { Card, EmptyState, Icon } from '../../components/ui';
import { relTime } from './_utils';

export function ActivityTab({ targetId }: { targetId: string }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['target-activity', targetId],
    queryFn: () => api.listTargetActivity(targetId, 200),
    refetchInterval: 10_000,
  });
  if (isLoading) return <div className="text-sm text-text-muted">Loading activity…</div>;
  if (error)
    return (
      <Card>
        <div className="text-sm text-sev-critical">{String(error)}</div>
      </Card>
    );
  const events = data ?? [];
  if (events.length === 0)
    return (
      <Card>
        <EmptyState
          icon={<Icon.Activity size={20} />}
          title="No activity yet"
          description="Audit events will appear here as scans run, approvals are decided and findings are triaged."
        />
      </Card>
    );
  return (
    <Card padded={false}>
      <ul className="divide-y divide-bg-line/60">
        {events.map((e) => (
          <ActivityRow key={e.id} event={e} />
        ))}
      </ul>
    </Card>
  );
}

function ActivityRow({ event }: { event: ActivityEvent }) {
  const tone = activityTone(event.event);
  return (
    <li className="flex items-start gap-3 px-5 py-3">
      <div className={`mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded ring-1 ${tone.cls}`}>
        {tone.icon}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs text-text-primary">{event.event}</span>
          {event.scan_id && (
            <Link
              to={`/scans/${event.scan_id}`}
              className="font-mono text-2xs text-text-muted hover:text-brand"
            >
              · {event.scan_id.slice(0, 8)}
            </Link>
          )}
        </div>
        <div className="mt-0.5 text-2xs text-text-muted">
          {event.actor ?? '—'} · {relTime(event.created_at)}
        </div>
        {Object.keys(event.payload || {}).length > 0 && (
          <pre className="mt-2 overflow-x-auto rounded bg-bg-overlay px-2 py-1.5 font-mono text-2xs text-text-secondary">
            {JSON.stringify(event.payload, null, 2)}
          </pre>
        )}
      </div>
    </li>
  );
}

function activityTone(event: string): { cls: string; icon: React.ReactNode } {
  if (event.startsWith('scan.guardrail') || event.startsWith('scan.hitl_denied'))
    return {
      cls: 'bg-sev-critical/10 text-sev-critical ring-sev-critical/30',
      icon: <Icon.Shield size={12} />,
    };
  if (event.includes('approval'))
    return {
      cls: 'bg-accent-warn/10 text-accent-warn ring-accent-warn/30',
      icon: <Icon.Inbox size={12} />,
    };
  if (event.endsWith('.finished') || event.endsWith('.started'))
    return {
      cls: 'bg-brand/10 text-brand ring-brand/30',
      icon: <Icon.Activity size={12} />,
    };
  return {
    cls: 'bg-bg-overlay text-text-secondary ring-bg-line',
    icon: <Icon.Activity size={12} />,
  };
}
