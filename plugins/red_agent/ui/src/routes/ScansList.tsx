import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useSearchParams } from 'react-router-dom';
import { Virtuoso } from 'react-virtuoso';
import { api, type ScanRow, type ScanStatus } from '../lib/api';
import {
  Button,
  Card,
  Chip,
  ConfirmDialog,
  EmptyState,
  Icon,
  MenuItem,
  PageHeader,
  Popover,
  StatusBadge,
} from '../components/ui';

const TERMINAL_SCAN_STATES: ScanStatus[] = ['completed', 'failed', 'cancelled'];

const STATUSES: { value: string; label: string }[] = [
  { value: '', label: 'All statuses' },
  { value: 'queued', label: 'Queued' },
  { value: 'awaiting_approval', label: 'Awaiting approval' },
  { value: 'running', label: 'Running' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
  { value: 'cancelled', label: 'Cancelled' },
];

const INTENSITY_TONE: Record<ScanRow['intensity'], 'neutral' | 'warn' | 'critical'> = {
  passive: 'neutral',
  active: 'warn',
  intrusive: 'critical',
};

function relTime(iso: string | null): string {
  if (!iso) return '—';
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return new Date(iso).toLocaleDateString();
}

export function ScansList() {
  const [params] = useSearchParams();
  const engagementId = params.get('engagement_id') ?? undefined;
  const [status, setStatus] = useState('');
  const [search, setSearch] = useState('');
  const [confirmDelete, setConfirmDelete] = useState<ScanRow | null>(null);
  const qc = useQueryClient();

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['scans', 'list', status, engagementId],
    queryFn: () =>
      api.listScans({
        status_filter: status || undefined,
        engagement_id: engagementId,
        limit: 200,
      }),
    refetchInterval: 5000,
  });

  const remove = useMutation({
    mutationFn: (id: string) => api.deleteScan(id),
    onSuccess: () => {
      setConfirmDelete(null);
      qc.invalidateQueries({ queryKey: ['scans'] });
    },
  });

  const rows: ScanRow[] = useMemo(() => {
    const all = data ?? [];
    if (!search) return all;
    const q = search.toLowerCase();
    return all.filter(
      (r) =>
        r.target_value.toLowerCase().includes(q) ||
        r.scanners.some((s) => s.toLowerCase().includes(q)) ||
        r.id.toLowerCase().startsWith(q)
    );
  }, [data, search]);

  const counts = useMemo(() => {
    const all = data ?? [];
    return {
      total: all.length,
      running: all.filter((x) => x.status === 'running' || x.status === 'queued').length,
      pending: all.filter((x) => x.status === 'awaiting_approval').length,
      failed: all.filter((x) => x.status === 'failed').length,
    };
  }, [data]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Scans"
        description="All launched scans, live status, and history."
        breadcrumbs={[{ label: 'Workspace' }, { label: 'Scans' }]}
        actions={
          <>
            <Button variant="secondary" onClick={() => refetch()} disabled={isFetching}>
              <Icon.Refresh size={14} />
              Refresh
            </Button>
            <Link to="/scans/new" className="ra-btn ra-btn-primary">
              <Icon.Plus size={14} />
              New scan
            </Link>
          </>
        }
        meta={
          <div className="flex flex-wrap gap-2 text-xs">
            <Chip>Total · {counts.total}</Chip>
            <Chip tone="brand">Running · {counts.running}</Chip>
            {counts.pending > 0 && <Chip tone="warn">Pending approval · {counts.pending}</Chip>}
            {counts.failed > 0 && <Chip tone="critical">Failed · {counts.failed}</Chip>}
          </div>
        }
      />

      <Card padded={false}>
        <div className="flex flex-wrap items-center gap-3 border-b border-bg-line p-4">
          <div className="relative flex-1 min-w-[220px]">
            <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-text-muted">
              <Icon.Search size={14} />
            </span>
            <input
              placeholder="Search by target, scanner, scan id…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="ra-input pl-9"
            />
          </div>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="ra-select w-44"
          >
            {STATUSES.map((s) => (
              <option key={s.value} value={s.value}>
                {s.label}
              </option>
            ))}
          </select>
        </div>

        {isLoading ? (
          <div className="grid place-items-center py-16 text-sm text-text-muted">
            <span className="font-mono">Loading scans…</span>
          </div>
        ) : error ? (
          <div className="m-4 rounded border border-sev-critical/40 bg-sev-critical/10 p-3 text-sm text-sev-critical">
            {String(error)}
          </div>
        ) : rows.length === 0 ? (
          <EmptyState
            icon={<Icon.Scans size={20} />}
            title="No scans found"
            description={search ? 'Try a different search.' : 'Launch your first scan.'}
            action={
              !search ? (
                <Link to="/scans/new" className="ra-btn ra-btn-primary">
                  <Icon.Plus size={14} />
                  New scan
                </Link>
              ) : null
            }
          />
        ) : (
          <div>
            <div className="grid grid-cols-[2fr_1.2fr_0.8fr_1fr_1.5fr_2.25rem] gap-2 border-b border-bg-line bg-bg-elevated/60 px-4 py-2.5 text-2xs font-mono font-semibold uppercase tracking-wider text-text-muted">
              <span>Target</span>
              <span>Status</span>
              <span>Intensity</span>
              <span>Started</span>
              <span>Scanners</span>
              <span aria-hidden="true" />
            </div>
            <Virtuoso
              style={{ height: '65vh' }}
              totalCount={rows.length}
              itemContent={(index) => {
                const r = rows[index]!;
                const terminal = TERMINAL_SCAN_STATES.includes(r.status);
                return (
                  <Link
                    to={`/scans/${r.id}`}
                    className="group grid grid-cols-[2fr_1.2fr_0.8fr_1fr_1.5fr_2.25rem] items-center gap-2 border-b border-bg-line/50 px-4 py-3 text-sm transition-colors hover:bg-bg-hover/50"
                  >
                    <div className="min-w-0">
                      <div className="truncate font-mono text-text-primary">{r.target_value}</div>
                      <div className="mt-0.5 truncate font-mono text-2xs text-text-muted">
                        {r.id.slice(0, 8)} · {r.requested_by}
                      </div>
                    </div>
                    <StatusBadge status={r.status} />
                    <Chip tone={INTENSITY_TONE[r.intensity]} className="w-fit">
                      {r.intensity}
                    </Chip>
                    <span className="font-mono text-xs text-text-muted">
                      {relTime(r.started_at)}
                    </span>
                    <div className="flex flex-wrap gap-1">
                      {r.scanners.slice(0, 4).map((s) => (
                        <Chip key={s}>{s}</Chip>
                      ))}
                      {r.scanners.length > 4 && <Chip>+{r.scanners.length - 4}</Chip>}
                    </div>
                    <div
                      className="opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100"
                      onClickCapture={(e) => {
                        e.preventDefault();
                      }}
                    >
                      <Popover
                        align="right"
                        width={220}
                        trigger={
                          <button
                            type="button"
                            aria-label="Scan actions"
                            className="grid h-7 w-7 place-items-center rounded text-text-muted hover:bg-bg-hover hover:text-text-primary"
                          >
                            <Icon.MoreVertical size={14} />
                          </button>
                        }
                      >
                        {(close) => (
                          <div className="py-1">
                            <MenuItem
                              icon={<Icon.Trash size={14} />}
                              label="Delete scan"
                              description={
                                terminal ? 'Remove run and findings' : 'Cancel the scan first'
                              }
                              danger
                              disabled={!terminal}
                              onSelect={() => {
                                setConfirmDelete(r);
                                close();
                              }}
                            />
                          </div>
                        )}
                      </Popover>
                    </div>
                  </Link>
                );
              }}
            />
          </div>
        )}
      </Card>

      <ConfirmDialog
        open={confirmDelete !== null}
        onClose={() => setConfirmDelete(null)}
        onConfirm={() => (confirmDelete ? remove.mutateAsync(confirmDelete.id) : Promise.resolve())}
        title="Delete scan permanently?"
        description={
          confirmDelete && (
            <>
              Run{' '}
              <span className="font-mono text-text-primary">{confirmDelete.id.slice(0, 8)}</span>{' '}
              against{' '}
              <span className="font-mono text-text-primary">{confirmDelete.target_value}</span> and
              all of its findings will be removed.
            </>
          )
        }
        consequences={[
          'All findings discovered in this run will be deleted.',
          'Audit log entries are preserved for compliance.',
          'This action cannot be undone.',
        ]}
        acknowledgement="I understand this run and its findings will be permanently deleted."
        confirmLabel="Delete forever"
        tone="danger"
        busy={remove.isPending}
      />
    </div>
  );
}
