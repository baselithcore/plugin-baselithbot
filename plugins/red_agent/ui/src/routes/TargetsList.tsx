import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { Virtuoso } from 'react-virtuoso';
import { api, type TargetKind, type TargetRecord } from '../lib/api';
import {
  Button,
  Card,
  Chip,
  ConfirmDialog,
  EmptyState,
  Icon,
  MenuDivider,
  MenuItem,
  PageHeader,
  Popover,
} from '../components/ui';
import { KIND_META, KIND_ORDER, postureRiskScore, riskBand } from '../lib/targets';

const KIND_TONE_TEXT: Record<TargetKind, string> = {
  web: 'text-cyan-300',
  cloud: 'text-violet-300',
  network: 'text-emerald-300',
  host: 'text-amber-300',
  repo: 'text-pink-300',
  binary: 'text-slate-300',
};

const RISK_COLOR: Record<'success' | 'neutral' | 'warn' | 'critical', string> = {
  success: 'bg-status-success',
  neutral: 'bg-brand',
  warn: 'bg-accent-warn',
  critical: 'bg-sev-critical',
};

function relTime(iso: string | null): string {
  if (!iso) return 'never';
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

function KindIcon({ kind, size = 14 }: { kind: TargetKind; size?: number }) {
  switch (kind) {
    case 'web':
      return <Icon.Globe size={size} />;
    case 'cloud':
      return <Icon.Cloud size={size} />;
    case 'network':
      return <Icon.Network size={size} />;
    case 'host':
      return <Icon.Server size={size} />;
    case 'repo':
      return <Icon.Folder size={size} />;
    case 'binary':
      return <Icon.Bug size={size} />;
  }
}

function TargetRow({ t }: { t: TargetRecord }) {
  const qc = useQueryClient();
  const postureQ = useQuery({
    queryKey: ['target-posture', t.id],
    queryFn: () => api.getTargetPosture(t.id),
    staleTime: 30_000,
  });
  const score = postureRiskScore(postureQ.data);
  const band = riskBand(score);
  const sev = postureQ.data?.severity_counts ?? {};
  const overdue = postureQ.data?.overdue ?? 0;
  const [confirmDelete, setConfirmDelete] = useState(false);
  const archived = t.archived_at !== null;

  const archive = useMutation({
    mutationFn: () => api.deleteTarget(t.id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['targets'] }),
  });
  const remove = useMutation({
    mutationFn: () => api.deleteTarget(t.id, { hard: true, purgeRuns: true }),
    onSuccess: () => {
      setConfirmDelete(false);
      qc.invalidateQueries({ queryKey: ['targets'] });
    },
  });

  return (
    <>
      <Link
        to={`/targets/${t.id}`}
        className="group grid grid-cols-[2.4fr_0.9fr_1.2fr_1.4fr_1fr_0.8fr_2.25rem] items-center gap-3 border-b border-bg-line/50 px-5 py-3.5 transition-colors hover:bg-bg-hover/50"
      >
        <div className="min-w-0 flex items-center gap-3">
          <div
            className={`grid h-9 w-9 shrink-0 place-items-center rounded-md bg-bg-overlay ring-1 ring-bg-line ${KIND_TONE_TEXT[t.kind]}`}
          >
            <KindIcon kind={t.kind} size={16} />
          </div>
          <div className="min-w-0">
            <div className="truncate font-medium text-text-primary">{t.name}</div>
            <div className="mt-0.5 truncate font-mono text-2xs text-text-muted">{t.value}</div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {t.environment && <Chip>{t.environment}</Chip>}
        </div>
        <div className="flex items-center gap-2 text-xs text-text-muted">
          <Icon.User size={11} />
          <span className="truncate">{t.owner ?? 'unassigned'}</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex h-1.5 w-24 overflow-hidden rounded bg-bg-overlay">
            <div
              className={`h-full transition-all ${RISK_COLOR[band.tone]}`}
              style={{ width: `${score}%` }}
            />
          </div>
          <span className="font-mono text-xs tabular-nums text-text-secondary">{score}</span>
          <span
            className={`text-2xs uppercase tracking-wider ${
              band.tone === 'critical'
                ? 'text-sev-critical'
                : band.tone === 'warn'
                  ? 'text-accent-warn'
                  : band.tone === 'success'
                    ? 'text-status-success'
                    : 'text-text-muted'
            }`}
          >
            {band.label}
          </span>
        </div>
        <div className="flex items-center gap-1.5 text-2xs font-mono">
          {(sev.critical ?? 0) > 0 && (
            <span className="rounded bg-sev-critical/15 px-1.5 py-0.5 text-sev-critical ring-1 ring-sev-critical/30">
              {sev.critical}C
            </span>
          )}
          {(sev.high ?? 0) > 0 && (
            <span className="rounded bg-accent-warn/15 px-1.5 py-0.5 text-accent-warn ring-1 ring-accent-warn/30">
              {sev.high}H
            </span>
          )}
          {(sev.medium ?? 0) > 0 && (
            <span className="rounded bg-bg-overlay px-1.5 py-0.5 text-text-secondary ring-1 ring-bg-line">
              {sev.medium}M
            </span>
          )}
          {overdue > 0 && (
            <span className="ml-1 inline-flex items-center gap-1 rounded bg-sev-critical/10 px-1.5 py-0.5 text-sev-critical ring-1 ring-sev-critical/20">
              <Icon.Hourglass size={10} />
              {overdue}
            </span>
          )}
          {(sev.critical ?? 0) + (sev.high ?? 0) + (sev.medium ?? 0) === 0 && overdue === 0 && (
            <span className="text-text-muted">—</span>
          )}
        </div>
        <div className="font-mono text-xs text-text-muted">{relTime(t.last_scan_at)}</div>
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
                aria-label="Target actions"
                className="grid h-7 w-7 place-items-center rounded text-text-muted hover:bg-bg-hover hover:text-text-primary"
              >
                <Icon.MoreVertical size={14} />
              </button>
            }
          >
            {(close) => (
              <div className="py-1">
                <MenuItem
                  icon={<Icon.Archive size={14} />}
                  label={archived ? 'Already archived' : 'Archive'}
                  description="Hide from active list, keep history"
                  disabled={archived || archive.isPending}
                  onSelect={() => {
                    archive.mutate();
                    close();
                  }}
                />
                <MenuDivider />
                <MenuItem
                  icon={<Icon.Trash size={14} />}
                  label="Delete permanently"
                  description="Removes runs and findings"
                  danger
                  onSelect={() => {
                    setConfirmDelete(true);
                    close();
                  }}
                />
              </div>
            )}
          </Popover>
        </div>
      </Link>
      <ConfirmDialog
        open={confirmDelete}
        onClose={() => setConfirmDelete(false)}
        onConfirm={() => remove.mutateAsync()}
        title="Delete target permanently?"
        description={
          <>
            You are about to delete <span className="font-mono text-text-primary">{t.name}</span>{' '}
            and every scan run and finding attached to it.
          </>
        }
        consequences={[
          'All scan runs against this target will be deleted.',
          'All findings discovered on this target will be deleted.',
          'This action cannot be undone.',
        ]}
        confirmText={t.name}
        confirmLabel="Delete forever"
        tone="danger"
        busy={remove.isPending}
      />
    </>
  );
}

export function TargetsList() {
  const [kindFilter, setKindFilter] = useState<TargetKind | 'all'>('all');
  const [search, setSearch] = useState('');
  const [includeArchived, setIncludeArchived] = useState(false);

  const { data, isLoading, isFetching, refetch, error } = useQuery({
    queryKey: ['targets', kindFilter, includeArchived],
    queryFn: () =>
      api.listTargets({
        kind: kindFilter === 'all' ? undefined : kindFilter,
        include_archived: includeArchived,
      }),
    refetchInterval: 30_000,
  });

  const rows = useMemo(() => {
    const all = data ?? [];
    if (!search) return all;
    const q = search.toLowerCase();
    return all.filter(
      (t) =>
        t.name.toLowerCase().includes(q) ||
        t.value.toLowerCase().includes(q) ||
        (t.owner ?? '').toLowerCase().includes(q) ||
        (t.environment ?? '').toLowerCase().includes(q) ||
        t.tags.some((x) => x.toLowerCase().includes(q))
    );
  }, [data, search]);

  const counts = useMemo(() => {
    const c: Record<TargetKind | 'all', number> = {
      all: 0,
      web: 0,
      cloud: 0,
      network: 0,
      host: 0,
      repo: 0,
      binary: 0,
    };
    for (const t of data ?? []) {
      c.all++;
      c[t.kind]++;
    }
    return c;
  }, [data]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Targets"
        description="Projects you scan over time. Profile, schedule, posture history."
        breadcrumbs={[{ label: 'Workspace' }, { label: 'Targets' }]}
        actions={
          <>
            <Button variant="secondary" onClick={() => refetch()} disabled={isFetching}>
              <Icon.Refresh size={14} />
              Refresh
            </Button>
            <Link to="/targets/new" className="ra-btn ra-btn-primary">
              <Icon.Plus size={14} />
              New target
            </Link>
          </>
        }
      />

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        {KIND_ORDER.map((k) => {
          const meta = KIND_META[k];
          const active = kindFilter === k;
          return (
            <button
              key={k}
              type="button"
              onClick={() => setKindFilter(active ? 'all' : k)}
              className={`group flex items-start gap-3 rounded-lg border bg-gradient-to-br p-3.5 text-left transition-all ${
                active
                  ? 'border-brand/60 ring-1 ring-brand/40'
                  : 'border-bg-line hover:border-bg-line-strong'
              } ${meta.accent}`}
            >
              <div className="grid h-9 w-9 place-items-center rounded-md bg-bg-elevated/80 ring-1 ring-current/20">
                <KindIcon kind={k} size={16} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between">
                  <div className="font-display text-sm font-medium text-text-primary">
                    {meta.shortLabel}
                  </div>
                  <span className="font-mono text-sm tabular-nums text-text-secondary">
                    {counts[k]}
                  </span>
                </div>
                <p className="mt-0.5 line-clamp-2 text-2xs text-text-muted">{meta.description}</p>
                {meta.comingSoon && (
                  <span className="mt-1 inline-block rounded bg-amber-500/10 px-1.5 py-0.5 text-2xs font-mono uppercase tracking-wider text-amber-300 ring-1 ring-amber-500/20">
                    coming soon
                  </span>
                )}
              </div>
            </button>
          );
        })}
      </div>

      <Card padded={false}>
        <div className="flex flex-wrap items-center gap-3 border-b border-bg-line p-4">
          <div className="relative flex-1 min-w-[260px]">
            <span className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-text-muted">
              <Icon.Search size={14} />
            </span>
            <input
              placeholder="Search by name, value, owner, env or tag…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="ra-input pl-9"
            />
          </div>
          <button
            type="button"
            onClick={() => setKindFilter('all')}
            className={`ra-btn ra-btn-ghost ra-btn-sm ${kindFilter === 'all' ? 'text-brand' : ''}`}
          >
            All ({counts.all})
          </button>
          <label className="flex items-center gap-2 text-xs text-text-muted">
            <input
              type="checkbox"
              checked={includeArchived}
              onChange={(e) => setIncludeArchived(e.target.checked)}
              className="accent-brand"
            />
            Show archived
          </label>
        </div>

        {isLoading ? (
          <div className="grid place-items-center py-16 text-sm text-text-muted">
            <span className="font-mono">Loading targets…</span>
          </div>
        ) : error ? (
          <div className="m-4 rounded border border-sev-critical/40 bg-sev-critical/10 p-3 text-sm text-sev-critical">
            {String(error)}
          </div>
        ) : rows.length === 0 ? (
          <EmptyState
            icon={<Icon.Target size={20} />}
            title={search ? 'No matches' : 'No targets yet'}
            description={
              search ? 'Try a different search.' : 'Add a target to start tracking posture.'
            }
            action={
              !search && (
                <Link to="/targets/new" className="ra-btn ra-btn-primary">
                  <Icon.Plus size={14} />
                  New target
                </Link>
              )
            }
          />
        ) : (
          <>
            <div className="grid grid-cols-[2.4fr_0.9fr_1.2fr_1.4fr_1fr_0.8fr_2.25rem] gap-3 border-b border-bg-line bg-bg-elevated/60 px-5 py-2.5 text-2xs font-mono font-semibold uppercase tracking-wider text-text-muted">
              <span>Target</span>
              <span>Env</span>
              <span>Owner</span>
              <span>Risk score</span>
              <span>Open</span>
              <span>Last scan</span>
              <span aria-hidden="true" />
            </div>
            <Virtuoso
              style={{ height: '60vh' }}
              totalCount={rows.length}
              itemContent={(i) => <TargetRow t={rows[i]!} />}
            />
          </>
        )}
      </Card>
    </div>
  );
}
