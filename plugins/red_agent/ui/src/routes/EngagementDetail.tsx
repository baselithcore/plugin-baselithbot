import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  api,
  type AutonomyLevel,
  type EngagementRecord,
  type EngagementStatus,
  type EngagementUpdate,
  type ScanIntensity,
  type ScanRow,
} from '../lib/api';
import { Button, Card, Chip, EmptyState, Icon, PageHeader, StatusBadge } from '../components/ui';
import { GovernanceTrendCard } from './Dashboard';
import { EngagementActivityCard, GovernanceStatsCard } from './engagement_detail/cards';
import { joinLines, relTime, splitLines } from './engagement_detail/helpers';

const STATUS_TONE: Record<EngagementStatus, 'neutral' | 'brand' | 'warn' | 'good' | 'critical'> = {
  draft: 'neutral',
  active: 'brand',
  paused: 'warn',
  completed: 'good',
  archived: 'critical',
};

const STATUSES: EngagementStatus[] = ['draft', 'active', 'paused', 'completed'];
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

export function EngagementDetail() {
  const { id = '' } = useParams<{ id: string }>();
  const nav = useNavigate();
  const qc = useQueryClient();

  const engagementQ = useQuery({
    queryKey: ['engagement', id],
    queryFn: () => api.getEngagement(id),
    enabled: Boolean(id),
  });
  const scansQ = useQuery({
    queryKey: ['scans', 'engagement', id],
    queryFn: () => api.listScans({ engagement_id: id, limit: 50 }),
    enabled: Boolean(id),
    refetchInterval: 10_000,
  });

  const update = useMutation({
    mutationFn: (body: EngagementUpdate) => api.updateEngagement(id, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['engagement', id] });
      qc.invalidateQueries({ queryKey: ['engagements'] });
    },
  });
  const archive = useMutation({
    mutationFn: () => api.archiveEngagement(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['engagements'] });
      nav('/engagements');
    },
  });

  const [form, setForm] = useState<EngagementUpdate | null>(null);
  const [scope, setScope] = useState('');
  const [excluded, setExcluded] = useState('');

  useEffect(() => {
    if (!engagementQ.data) return;
    const e = engagementQ.data;
    setForm({
      name: e.name,
      objective: e.objective,
      status: e.status,
      tags: e.tags,
      rules: { ...e.rules },
    });
    setScope(joinLines(e.rules.scope_allowlist));
    setExcluded(joinLines(e.rules.excluded_targets));
  }, [engagementQ.data]);

  const dirty = useMemo(() => {
    if (!engagementQ.data || !form) return false;
    const e = engagementQ.data;
    if (form.name !== e.name) return true;
    if (form.objective !== e.objective) return true;
    if (form.status !== e.status) return true;
    if ((form.tags ?? []).join(',') !== e.tags.join(',')) return true;
    const r = form.rules ?? {};
    if (r.autonomy_level !== e.rules.autonomy_level) return true;
    if (r.max_intensity !== e.rules.max_intensity) return true;
    if (r.require_human_approval !== e.rules.require_human_approval) return true;
    if (joinLines(r.scope_allowlist ?? []) !== joinLines(e.rules.scope_allowlist)) return true;
    if (joinLines(r.excluded_targets ?? []) !== joinLines(e.rules.excluded_targets)) return true;
    return false;
  }, [engagementQ.data, form]);

  function save() {
    if (!form) return;
    const body: EngagementUpdate = {
      ...form,
      rules: {
        ...(form.rules ?? {}),
        scope_allowlist: splitLines(scope),
        excluded_targets: splitLines(excluded),
      },
    };
    update.mutate(body);
  }

  if (engagementQ.isLoading) {
    return <div className="grid place-items-center py-16 font-mono text-text-muted">Loading…</div>;
  }
  if (engagementQ.error || !engagementQ.data) {
    return (
      <div className="m-6 rounded border border-sev-critical/40 bg-sev-critical/10 p-4 text-sm text-sev-critical">
        {String(engagementQ.error ?? 'engagement not found')}
      </div>
    );
  }

  const e: EngagementRecord = engagementQ.data;
  const scans: ScanRow[] = scansQ.data ?? [];

  return (
    <div className="space-y-5">
      <PageHeader
        title={e.name}
        description={e.objective}
        breadcrumbs={[
          { label: 'Workspace' },
          { label: 'Engagements', to: '/engagements' },
          { label: e.name },
        ]}
        meta={
          <div className="flex flex-wrap gap-2 text-xs">
            <Chip tone={STATUS_TONE[e.status]}>{e.status}</Chip>
            <Chip>autonomy · {AUTONOMY_LABEL[e.rules.autonomy_level ?? 'recommend']}</Chip>
            <Chip>max · {e.rules.max_intensity}</Chip>
            {e.rules.require_human_approval && <Chip tone="warn">HITL forced</Chip>}
            <Chip>created {relTime(e.created_at)}</Chip>
          </div>
        }
        actions={
          <div className="flex gap-2">
            <a
              href={api.engagementSigmaBundleUrl(e.id)}
              target="_blank"
              rel="noopener noreferrer"
              download
              className="ra-btn ra-btn-ghost"
            >
              <Icon.Download size={14} />
              Sigma bundle
            </a>
            <Button
              variant="ghost"
              onClick={() => archive.mutate()}
              disabled={e.status === 'archived' || archive.isPending}
            >
              <Icon.Trash size={14} />
              Archive
            </Button>
            <Button variant="primary" onClick={save} disabled={!dirty || update.isPending}>
              {update.isPending ? 'Saving…' : 'Save changes'}
            </Button>
          </div>
        }
      />

      {update.error && (
        <div className="rounded border border-sev-critical/40 bg-sev-critical/10 p-3 text-sm text-sev-critical">
          {String(update.error)}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-[1fr_1fr]">
        <Card title="Mission" subtitle="Identity, status, tags">
          <div className="space-y-3">
            <Field label="Name">
              <input
                value={form?.name ?? ''}
                onChange={(ev) => setForm((s) => ({ ...(s ?? {}), name: ev.target.value }))}
                className="ra-input"
              />
            </Field>
            <Field label="Objective">
              <textarea
                value={form?.objective ?? ''}
                onChange={(ev) => setForm((s) => ({ ...(s ?? {}), objective: ev.target.value }))}
                className="ra-input min-h-[88px]"
              />
            </Field>
            <Field label="Status">
              <select
                value={form?.status ?? e.status}
                onChange={(ev) =>
                  setForm((s) => ({ ...(s ?? {}), status: ev.target.value as EngagementStatus }))
                }
                className="ra-select"
              >
                {STATUSES.map((x) => (
                  <option key={x} value={x}>
                    {x}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Tags (comma)">
              <input
                value={(form?.tags ?? []).join(', ')}
                onChange={(ev) =>
                  setForm((s) => ({
                    ...(s ?? {}),
                    tags: ev.target.value
                      .split(',')
                      .map((t) => t.trim())
                      .filter(Boolean),
                  }))
                }
                className="ra-input"
              />
            </Field>
          </div>
        </Card>

        <Card title="Rules of engagement" subtitle="Scope, exclusions, autonomy ladder">
          <div className="grid gap-3 sm:grid-cols-2">
            <Field label="Max intensity">
              <select
                value={form?.rules?.max_intensity ?? e.rules.max_intensity}
                onChange={(ev) =>
                  setForm((s) => ({
                    ...(s ?? {}),
                    rules: {
                      ...(s?.rules ?? {}),
                      max_intensity: ev.target.value as ScanIntensity,
                    },
                  }))
                }
                className="ra-select"
              >
                {INTENSITIES.map((x) => (
                  <option key={x} value={x}>
                    {x}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Autonomy">
              <select
                value={form?.rules?.autonomy_level ?? e.rules.autonomy_level ?? 'recommend'}
                onChange={(ev) =>
                  setForm((s) => ({
                    ...(s ?? {}),
                    rules: {
                      ...(s?.rules ?? {}),
                      autonomy_level: ev.target.value as AutonomyLevel,
                    },
                  }))
                }
                className="ra-select"
              >
                {AUTONOMY_LEVELS.map((x) => (
                  <option key={x} value={x}>
                    {AUTONOMY_LABEL[x]}
                  </option>
                ))}
              </select>
            </Field>
            <label className="col-span-2 flex items-center gap-2 text-sm text-text-secondary">
              <input
                type="checkbox"
                checked={form?.rules?.require_human_approval ?? e.rules.require_human_approval}
                onChange={(ev) =>
                  setForm((s) => ({
                    ...(s ?? {}),
                    rules: {
                      ...(s?.rules ?? {}),
                      require_human_approval: ev.target.checked,
                    },
                  }))
                }
                className="accent-brand"
              />
              Require human approval on every scan (force HITL)
            </label>
          </div>
          <div className="mt-3 grid gap-3 sm:grid-cols-2">
            <Field label="Scope allowlist">
              <textarea
                value={scope}
                onChange={(ev) => setScope(ev.target.value)}
                className="ra-input min-h-[110px] font-mono text-xs"
                placeholder={'example.com\napi.example.com\n203.0.113.0/24'}
              />
            </Field>
            <Field label="Excluded targets">
              <textarea
                value={excluded}
                onChange={(ev) => setExcluded(ev.target.value)}
                className="ra-input min-h-[110px] font-mono text-xs"
                placeholder={'status.example.com\nlegacy-admin.example.com'}
              />
            </Field>
          </div>
        </Card>
      </div>

      <GovernanceStatsCard engagementId={id} />
      <GovernanceTrendCard engagementId={id} />
      <EngagementActivityCard engagementId={id} />

      <Card
        title="Scans in this engagement"
        subtitle={`${scans.length} run${scans.length === 1 ? '' : 's'}`}
        action={
          <Link
            to={`/scans/new?engagement_id=${e.id}`}
            className="ra-btn ra-btn-secondary ra-btn-sm"
          >
            <Icon.Plus size={12} />
            New scan
          </Link>
        }
        padded={false}
      >
        {scans.length === 0 ? (
          <EmptyState
            compact
            icon={<Icon.Scans size={20} />}
            title="No scans yet"
            description="Launch a scan with this engagement_id to see it here."
          />
        ) : (
          <ul className="divide-y divide-bg-line/60">
            {scans.map((s) => (
              <li key={s.id}>
                <Link
                  to={`/scans/${s.id}`}
                  className="flex items-center justify-between gap-4 px-5 py-3 hover:bg-bg-hover/50"
                >
                  <div className="min-w-0">
                    <div className="truncate font-mono text-xs text-text-primary">
                      {s.target_value}
                    </div>
                    <div className="mt-1 flex flex-wrap gap-2 text-2xs text-text-muted">
                      <span>{relTime(s.started_at)}</span>
                      <Chip>{s.intensity}</Chip>
                      {s.scanners.slice(0, 4).map((sc) => (
                        <Chip key={sc}>{sc}</Chip>
                      ))}
                    </div>
                  </div>
                  <StatusBadge status={s.status} />
                </Link>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="mb-1.5 block text-2xs font-mono uppercase tracking-wider text-text-muted">
        {label}
      </label>
      {children}
    </div>
  );
}
