import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  api,
  type AutonomyLevel,
  type EngagementCreate,
  type EngagementRecord,
  type EngagementStatus,
  type ScanIntensity,
} from '../lib/api';
import { Button, Card, Chip, EmptyState, Icon, PageHeader } from '../components/ui';

const STATUS_TONE: Record<EngagementStatus, 'neutral' | 'brand' | 'warn' | 'good' | 'critical'> = {
  draft: 'neutral',
  active: 'brand',
  paused: 'warn',
  completed: 'good',
  archived: 'critical',
};

const INTENSITIES: ScanIntensity[] = ['passive', 'active', 'intrusive'];

const AUTONOMY_LEVELS: AutonomyLevel[] = [
  'observe',
  'plan',
  'recommend',
  'execute_passive',
  'execute_active',
  'execute_intrusive',
];

const AUTONOMY_LABEL: Record<AutonomyLevel, string> = {
  observe: 'Observe',
  plan: 'Plan',
  recommend: 'Recommend',
  execute_passive: 'Execute · passive',
  execute_active: 'Execute · active (HITL)',
  execute_intrusive: 'Execute · intrusive (HITL)',
};

function relTime(iso: string): string {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return new Date(iso).toLocaleDateString();
}

function splitLines(value: string): string[] {
  return value
    .split('\n')
    .map((x) => x.trim())
    .filter(Boolean);
}

export function Engagements() {
  const qc = useQueryClient();
  const [showCreate, setShowCreate] = useState(false);
  const [name, setName] = useState('');
  const [objective, setObjective] = useState('');
  const [scope, setScope] = useState('');
  const [excluded, setExcluded] = useState('');
  const [maxIntensity, setMaxIntensity] = useState<ScanIntensity>('passive');
  const [autonomyLevel, setAutonomyLevel] = useState<AutonomyLevel>('recommend');
  const [requireApproval, setRequireApproval] = useState(true);
  const [tags, setTags] = useState('');

  const [statusFilter, setStatusFilter] = useState<EngagementStatus | 'all'>('all');
  const [includeArchived, setIncludeArchived] = useState(false);

  const engagements = useQuery({
    queryKey: ['engagements', statusFilter, includeArchived],
    queryFn: () =>
      api.listEngagements({
        status_filter: statusFilter === 'all' ? undefined : statusFilter,
        include_archived: includeArchived,
        limit: 100,
      }),
    refetchInterval: 30_000,
  });

  const create = useMutation({
    mutationFn: (body: EngagementCreate) => api.createEngagement(body),
    onSuccess: () => {
      setShowCreate(false);
      setName('');
      setObjective('');
      setScope('');
      setExcluded('');
      setMaxIntensity('passive');
      setAutonomyLevel('recommend');
      setRequireApproval(true);
      setTags('');
      qc.invalidateQueries({ queryKey: ['engagements'] });
    },
  });

  const counts = useMemo(() => {
    const rows = engagements.data ?? [];
    return {
      total: rows.length,
      active: rows.filter((x) => x.status === 'active').length,
      draft: rows.filter((x) => x.status === 'draft').length,
      paused: rows.filter((x) => x.status === 'paused').length,
      completed: rows.filter((x) => x.status === 'completed').length,
      archived: rows.filter((x) => x.status === 'archived').length,
    };
  }, [engagements.data]);

  const FILTER_OPTIONS: (EngagementStatus | 'all')[] = [
    'all',
    'draft',
    'active',
    'paused',
    'completed',
    'archived',
  ];

  function submit() {
    create.mutate({
      name,
      objective,
      tags: tags
        .split(',')
        .map((x) => x.trim())
        .filter(Boolean),
      rules: {
        scope_allowlist: splitLines(scope),
        excluded_targets: splitLines(excluded),
        max_intensity: maxIntensity,
        autonomy_level: autonomyLevel,
        require_human_approval: requireApproval,
        testing_window: null,
        notes: null,
      },
    });
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="Engagements"
        description="Scope, rules, campaign context."
        breadcrumbs={[{ label: 'Workspace' }, { label: 'Engagements' }]}
        meta={
          <div className="flex flex-wrap gap-2 text-xs">
            <Chip>Total · {counts.total}</Chip>
            <Chip tone="brand">Active · {counts.active}</Chip>
            <Chip>Draft · {counts.draft}</Chip>
            <Chip tone="good">Completed · {counts.completed}</Chip>
          </div>
        }
        actions={
          <Button variant="primary" onClick={() => setShowCreate((x) => !x)}>
            <Icon.Plus size={14} />
            New engagement
          </Button>
        }
      />

      {showCreate && (
        <Card title="New engagement" subtitle="Set objective and rules of engagement">
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="space-y-3">
              <div>
                <label className="mb-1.5 block text-2xs font-mono uppercase tracking-wider text-text-muted">
                  Name
                </label>
                <input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="ra-input"
                  placeholder="Q2 external attack surface validation"
                />
              </div>
              <div>
                <label className="mb-1.5 block text-2xs font-mono uppercase tracking-wider text-text-muted">
                  Objective
                </label>
                <textarea
                  value={objective}
                  onChange={(e) => setObjective(e.target.value)}
                  className="ra-input min-h-[96px]"
                  placeholder="Validate exploitable paths from public web entrypoints to sensitive systems."
                />
              </div>
              <div>
                <label className="mb-1.5 block text-2xs font-mono uppercase tracking-wider text-text-muted">
                  Tags
                </label>
                <input
                  value={tags}
                  onChange={(e) => setTags(e.target.value)}
                  className="ra-input"
                  placeholder="external, q2, appsec"
                />
              </div>
            </div>
            <div className="space-y-3">
              <div>
                <label className="mb-1.5 block text-2xs font-mono uppercase tracking-wider text-text-muted">
                  Scope allowlist
                </label>
                <textarea
                  value={scope}
                  onChange={(e) => setScope(e.target.value)}
                  className="ra-input min-h-[88px] font-mono text-xs"
                  placeholder={'example.com\napi.example.com\n203.0.113.0/24'}
                />
              </div>
              <div>
                <label className="mb-1.5 block text-2xs font-mono uppercase tracking-wider text-text-muted">
                  Excluded targets
                </label>
                <textarea
                  value={excluded}
                  onChange={(e) => setExcluded(e.target.value)}
                  className="ra-input min-h-[72px] font-mono text-xs"
                  placeholder={'status.example.com\nlegacy-admin.example.com'}
                />
              </div>
              <div className="grid gap-3 sm:grid-cols-2">
                <div>
                  <label className="mb-1.5 block text-2xs font-mono uppercase tracking-wider text-text-muted">
                    Max intensity
                  </label>
                  <select
                    value={maxIntensity}
                    onChange={(e) => setMaxIntensity(e.target.value as ScanIntensity)}
                    className="ra-select"
                  >
                    {INTENSITIES.map((x) => (
                      <option key={x} value={x}>
                        {x}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-1.5 block text-2xs font-mono uppercase tracking-wider text-text-muted">
                    Autonomy
                  </label>
                  <select
                    value={autonomyLevel}
                    onChange={(e) => setAutonomyLevel(e.target.value as AutonomyLevel)}
                    className="ra-select"
                  >
                    {AUTONOMY_LEVELS.map((x) => (
                      <option key={x} value={x}>
                        {AUTONOMY_LABEL[x]}
                      </option>
                    ))}
                  </select>
                </div>
                <label className="flex items-end gap-2 pb-2 text-sm text-text-secondary sm:col-span-2">
                  <input
                    type="checkbox"
                    checked={requireApproval}
                    onChange={(e) => setRequireApproval(e.target.checked)}
                    className="accent-brand"
                  />
                  Require approval
                </label>
              </div>
            </div>
          </div>
          {create.error && (
            <div className="mt-4 rounded border border-sev-critical/40 bg-sev-critical/10 p-3 text-sm text-sev-critical">
              {String(create.error)}
            </div>
          )}
          <div className="mt-5 flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setShowCreate(false)}>
              Cancel
            </Button>
            <Button
              variant="primary"
              disabled={!name.trim() || !objective.trim() || create.isPending}
              onClick={submit}
            >
              {create.isPending ? 'Creating…' : 'Create engagement'}
            </Button>
          </div>
        </Card>
      )}

      <Card padded={false}>
        <div className="flex flex-wrap items-center gap-2 border-b border-bg-line/60 px-4 py-3">
          {FILTER_OPTIONS.map((opt) => {
            const active = statusFilter === opt;
            return (
              <button
                key={opt}
                type="button"
                onClick={() => {
                  setStatusFilter(opt);
                  if (opt === 'archived') setIncludeArchived(true);
                }}
                className={`rounded border px-2.5 py-1 text-2xs font-mono uppercase tracking-wider transition-colors ${
                  active
                    ? 'border-brand/60 bg-brand/10 text-brand'
                    : 'border-bg-line text-text-muted hover:text-text-primary'
                }`}
              >
                {opt}
                {opt !== 'all' && (
                  <span className="ml-1.5 text-text-subtle">{counts[opt as EngagementStatus]}</span>
                )}
              </button>
            );
          })}
          <label className="ml-auto flex items-center gap-2 text-2xs text-text-muted">
            <input
              type="checkbox"
              checked={includeArchived}
              onChange={(e) => setIncludeArchived(e.target.checked)}
              className="accent-brand"
            />
            include archived
          </label>
        </div>
        {engagements.isLoading ? (
          <div className="grid place-items-center py-16 text-sm text-text-muted">
            <span className="font-mono">Loading engagements…</span>
          </div>
        ) : engagements.error ? (
          <div className="m-4 rounded border border-sev-critical/40 bg-sev-critical/10 p-3 text-sm text-sev-critical">
            {String(engagements.error)}
          </div>
        ) : engagements.data && engagements.data.length > 0 ? (
          <div className="divide-y divide-bg-line/60">
            {engagements.data.map((engagement) => (
              <EngagementRow key={engagement.id} engagement={engagement} />
            ))}
          </div>
        ) : (
          <EmptyState
            icon={<Icon.Folder size={24} />}
            title="No engagements yet"
            description="Define one to scope a campaign."
            action={
              <Button variant="primary" onClick={() => setShowCreate(true)}>
                <Icon.Plus size={14} />
                New engagement
              </Button>
            }
          />
        )}
      </Card>
    </div>
  );
}

function EngagementRow({ engagement }: { engagement: EngagementRecord }) {
  return (
    <div className="grid gap-4 px-5 py-4 lg:grid-cols-[1.4fr_1fr_0.8fr_auto] lg:items-center">
      <div className="min-w-0">
        <div className="flex flex-wrap items-center gap-2">
          <Link
            to={`/engagements/${engagement.id}`}
            className="truncate font-display text-sm font-medium text-text-primary hover:text-brand"
          >
            {engagement.name}
          </Link>
          <Chip tone={STATUS_TONE[engagement.status]}>{engagement.status}</Chip>
        </div>
        <p className="mt-1 line-clamp-2 text-sm text-text-muted">{engagement.objective}</p>
        {engagement.tags.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1">
            {engagement.tags.slice(0, 5).map((tag) => (
              <Chip key={tag}>{tag}</Chip>
            ))}
          </div>
        )}
      </div>
      <div className="grid grid-cols-4 gap-2 text-xs">
        <Metric label="Scope" value={engagement.rules.scope_allowlist.length} />
        <Metric label="Excluded" value={engagement.rules.excluded_targets.length} />
        <Metric label="Max" value={engagement.rules.max_intensity} />
        <Metric label="Autonomy" value={engagement.rules.autonomy_level ?? 'recommend'} />
      </div>
      <div className="font-mono text-xs text-text-muted">
        created {relTime(engagement.created_at)}
      </div>
      <Link
        to={`/scans?engagement_id=${engagement.id}`}
        className="ra-btn ra-btn-secondary justify-center"
      >
        <Icon.Scans size={14} />
        Scans
      </Link>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded border border-bg-line bg-bg-elevated px-2 py-1.5">
      <div className="font-mono text-2xs uppercase tracking-wider text-text-muted">{label}</div>
      <div className="mt-0.5 truncate font-mono text-xs text-text-primary">{value}</div>
    </div>
  );
}
