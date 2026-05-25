import { Link } from 'react-router-dom';
import type { ScanRow, ScanStatus } from '../../lib/api';
import { Card, EmptyState, Icon, StatusBadge } from '../../components/ui';
import { relTime } from './_utils';

const ACTIVE: ScanStatus[] = ['running', 'queued', 'awaiting_approval'];

const STATUS_ACCENT: Partial<Record<ScanStatus, string>> = {
  running: 'bg-brand',
  queued: 'bg-text-muted',
  awaiting_approval: 'bg-accent-warn',
};

export function LiveOps({ scans }: { scans: ScanRow[] }) {
  const active = scans.filter((s) => ACTIVE.includes(s.status)).slice(0, 8);
  const running = active.filter((s) => s.status === 'running').length;
  const queued = active.filter((s) => s.status === 'queued').length;
  const awaiting = active.filter((s) => s.status === 'awaiting_approval').length;

  return (
    <Card
      title="Live operations"
      subtitle={`${running} running · ${queued} queued · ${awaiting} awaiting approval`}
      action={
        <Link to="/scans" className="ra-btn ra-btn-ghost ra-btn-sm">
          All scans
          <Icon.ArrowRight size={12} />
        </Link>
      }
      padded={false}
    >
      {active.length === 0 ? (
        <EmptyState
          compact
          icon={<Icon.Activity size={20} />}
          title="No active operations"
          description="Launch a scan from the command bar above."
        />
      ) : (
        <ul className="divide-y divide-bg-line/60">
          {active.map((sc) => (
            <li key={sc.id}>
              <Link
                to={`/scans/${sc.id}`}
                className="flex items-center gap-3 px-5 py-3 transition-colors hover:bg-bg-hover/50"
              >
                <span
                  className={`relative inline-flex h-2 w-2 shrink-0 rounded-full ${
                    STATUS_ACCENT[sc.status] ?? 'bg-text-muted'
                  }`}
                  aria-hidden
                >
                  {sc.status === 'running' && (
                    <span className="absolute inset-0 animate-ping rounded-full bg-brand/60" />
                  )}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="truncate font-mono text-xs text-text-primary">
                      {sc.target_value}
                    </span>
                    <span className="truncate font-mono text-2xs uppercase tracking-wider text-text-muted">
                      {sc.intensity}
                    </span>
                  </div>
                  <div className="mt-0.5 flex items-center gap-2 font-mono text-2xs text-text-muted">
                    <Icon.Clock size={10} />
                    <span>{relTime(sc.started_at)}</span>
                    {sc.scanners.length > 0 && (
                      <>
                        <span>·</span>
                        <span className="truncate">{sc.scanners.slice(0, 3).join(', ')}</span>
                        {sc.scanners.length > 3 && <span>+{sc.scanners.length - 3}</span>}
                      </>
                    )}
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
