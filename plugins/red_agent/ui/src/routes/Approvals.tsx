import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { api, getToken } from '../lib/api';
import { Button, Card, EmptyState, Icon, PageHeader } from '../components/ui';

interface PendingApproval {
  scan_id: string;
  reason: string;
  requested_by: string;
  opened_at: string;
}

async function fetchPending(): Promise<PendingApproval[]> {
  const res = await fetch('/red-agent/scans/pending-approvals', {
    headers: {
      Authorization: `Bearer ${getToken()}`,
    },
  });
  if (!res.ok) throw new Error(`${res.status}`);
  return res.json();
}

function relTime(iso: string): string {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  return `${Math.floor(diff / 3600)}h ago`;
}

export function Approvals() {
  const qc = useQueryClient();
  const { data, isLoading, error } = useQuery({
    queryKey: ['approvals', 'pending'],
    queryFn: fetchPending,
    refetchInterval: 5_000,
  });

  const approve = useMutation({
    mutationFn: (id: string) => api.approveScan(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['approvals', 'pending'] }),
  });
  const reject = useMutation({
    mutationFn: (id: string) => api.rejectScan(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['approvals', 'pending'] }),
  });

  const items = data ?? [];

  return (
    <div className="space-y-6">
      <PageHeader
        title="Approvals"
        description="Active and intrusive scans waiting for human-in-the-loop authorization."
        breadcrumbs={[{ label: 'Workspace' }, { label: 'Approvals' }]}
        badge={items.length > 0 ? { label: `${items.length} pending`, tone: 'beta' } : undefined}
      />

      {isLoading ? (
        <div className="text-sm text-text-muted">Loading…</div>
      ) : error ? (
        <Card>
          <div className="text-sm text-sev-critical">{String(error)}</div>
        </Card>
      ) : items.length === 0 ? (
        <Card>
          <EmptyState
            icon={<Icon.ShieldCheck size={20} />}
            title="No pending approvals"
            description="Active and intrusive scans queue here for review before launch."
          />
        </Card>
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <Card key={item.scan_id}>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="flex items-start gap-3">
                  <div className="grid h-10 w-10 shrink-0 place-items-center rounded-md bg-accent-warn/10 text-accent-warn ring-1 ring-accent-warn/30">
                    <Icon.Shield size={18} />
                  </div>
                  <div>
                    <Link
                      to={`/scans/${item.scan_id}`}
                      className="font-display text-sm font-medium text-text-primary hover:text-brand"
                    >
                      Scan {item.scan_id.slice(0, 8)}
                    </Link>
                    <p className="mt-0.5 text-sm text-text-muted">{item.reason}</p>
                    <p className="mt-1 text-2xs font-mono text-text-subtle">
                      requested by {item.requested_by} · {relTime(item.opened_at)}
                    </p>
                  </div>
                </div>
                <div className="flex gap-2 sm:shrink-0">
                  <Button
                    variant="primary"
                    onClick={() => approve.mutate(item.scan_id)}
                    disabled={approve.isPending}
                  >
                    <Icon.Check size={14} />
                    Approve
                  </Button>
                  <Button
                    variant="danger"
                    onClick={() => reject.mutate(item.scan_id)}
                    disabled={reject.isPending}
                  >
                    <Icon.X size={14} />
                    Reject
                  </Button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
