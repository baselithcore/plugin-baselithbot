import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link, useParams, useNavigate } from 'react-router-dom';
import { api, type TargetKind } from '../lib/api';
import { Button, Chip, Icon, PageHeader } from '../components/ui';
import { NewScanDialog } from './target_detail/NewScanDialog';
import { KIND_META, postureRiskScore, riskBand } from '../lib/targets';
import { OverviewTab } from './target_detail/OverviewTab';
import { RunsTab } from './target_detail/RunsTab';
import { FindingsTab } from './target_detail/FindingsTab';
import { ActivityTab } from './target_detail/ActivityTab';
import { SettingsTab } from './target_detail/SettingsTab';
import { SurfaceTab } from './target_detail/SurfaceTab';

type TabId = 'overview' | 'runs' | 'findings' | 'surface' | 'activity' | 'settings';

const TABS: { id: TabId; label: string; icon: React.ReactNode }[] = [
  { id: 'overview', label: 'Overview', icon: <Icon.Dashboard size={14} /> },
  { id: 'runs', label: 'Runs', icon: <Icon.Scans size={14} /> },
  { id: 'findings', label: 'Findings', icon: <Icon.Findings size={14} /> },
  { id: 'surface', label: 'Surface', icon: <Icon.Graph size={14} /> },
  { id: 'activity', label: 'Activity', icon: <Icon.Activity size={14} /> },
  { id: 'settings', label: 'Settings', icon: <Icon.Settings size={14} /> },
];

function KindIcon({ kind, size = 16 }: { kind: TargetKind; size?: number }) {
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

export function TargetDetail() {
  const { id = '' } = useParams();
  const nav = useNavigate();
  const qc = useQueryClient();
  const [tab, setTab] = useState<TabId>('overview');
  const [newScanOpen, setNewScanOpen] = useState(false);

  const targetQ = useQuery({
    queryKey: ['target', id],
    queryFn: () => api.getTarget(id),
    enabled: Boolean(id),
  });
  const postureQ = useQuery({
    queryKey: ['target-posture', id],
    queryFn: () => api.getTargetPosture(id),
    enabled: Boolean(id),
    refetchInterval: 15_000,
  });
  const runsQ = useQuery({
    queryKey: ['target-runs', id],
    queryFn: () => api.listTargetScans(id, { limit: 50 }),
    enabled: Boolean(id),
    refetchInterval: 5_000,
  });
  const findingsQ = useQuery({
    queryKey: ['target-findings', id],
    queryFn: () => api.listFindings({ target_id: id, limit: 200 }),
    enabled: Boolean(id),
  });

  const archive = useMutation({
    mutationFn: () => api.updateTarget(id, { archived: true }),
    onSuccess: () => nav('/targets'),
  });

  if (targetQ.isLoading) {
    return (
      <div className="grid place-items-center py-20 text-sm text-text-muted">
        <span className="font-mono">Loading target…</span>
      </div>
    );
  }
  if (targetQ.error || !targetQ.data) {
    return (
      <div className="rounded border border-sev-critical/40 bg-sev-critical/10 p-3 text-sm text-sev-critical">
        {String(targetQ.error ?? 'target not found')}
      </div>
    );
  }
  const target = targetQ.data;
  const posture = postureQ.data;
  const score = postureRiskScore(posture);
  const band = riskBand(score);
  const meta = KIND_META[target.kind];

  return (
    <div className="space-y-6">
      <PageHeader
        title={
          <span className="flex items-center gap-3">
            <span className="grid h-9 w-9 place-items-center rounded-md bg-bg-overlay text-text-secondary ring-1 ring-bg-line">
              <KindIcon kind={target.kind} size={18} />
            </span>
            <span>{target.name}</span>
            <span
              className={`inline-flex items-center rounded px-2 py-0.5 text-2xs font-mono uppercase tracking-wider ring-1 ring-inset ${
                band.tone === 'critical'
                  ? 'bg-sev-critical/15 text-sev-critical ring-sev-critical/30'
                  : band.tone === 'warn'
                    ? 'bg-accent-warn/15 text-accent-warn ring-accent-warn/30'
                    : band.tone === 'success'
                      ? 'bg-status-success/15 text-status-success ring-status-success/30'
                      : 'bg-brand/15 text-brand ring-brand/30'
              }`}
            >
              {band.label} · {score}
            </span>
          </span>
        }
        breadcrumbs={[{ label: 'Targets' }, { label: meta.shortLabel }, { label: target.name }]}
        meta={
          <div className="flex flex-wrap items-center gap-2 font-mono text-xs text-text-muted">
            <span>{target.value}</span>
            {target.environment && (
              <>
                <span>·</span>
                <Chip>{target.environment}</Chip>
              </>
            )}
            {target.owner && (
              <>
                <span>·</span>
                <span className="inline-flex items-center gap-1">
                  <Icon.User size={11} /> {target.owner}
                </span>
              </>
            )}
            {target.tags.map((t) => (
              <Chip key={t}>#{t}</Chip>
            ))}
          </div>
        }
        actions={
          <>
            <Button variant="secondary" onClick={() => setNewScanOpen(true)}>
              <Icon.Bolt size={14} />
              Run scan
            </Button>
            <Link to={`/targets/${id}?tab=settings`} className="ra-btn ra-btn-ghost">
              <Icon.Settings size={14} />
              Settings
            </Link>
          </>
        }
      />

      <div className="flex flex-wrap gap-1 border-b border-bg-line">
        {TABS.map((t) => {
          const active = tab === t.id;
          return (
            <button
              key={t.id}
              type="button"
              onClick={() => setTab(t.id)}
              className={`relative inline-flex items-center gap-2 px-3 py-2 text-sm font-medium transition-colors ${
                active ? 'text-brand' : 'text-text-secondary hover:text-text-primary'
              }`}
            >
              {t.icon}
              <span>{t.label}</span>
              {active && (
                <span className="absolute inset-x-2 -bottom-px h-0.5 rounded-t bg-brand shadow-glow-soft" />
              )}
            </button>
          );
        })}
      </div>

      {tab === 'overview' && (
        <OverviewTab
          target={target}
          posture={posture}
          findings={findingsQ.data ?? []}
          runs={runsQ.data ?? []}
        />
      )}
      {tab === 'runs' && (
        <RunsTab target={target} runs={runsQ.data ?? []} loading={runsQ.isLoading} />
      )}
      {tab === 'findings' && (
        <FindingsTab
          targetId={id}
          findings={findingsQ.data ?? []}
          loading={findingsQ.isLoading}
          onUpdate={() => qc.invalidateQueries({ queryKey: ['target-findings', id] })}
        />
      )}
      {tab === 'surface' && <SurfaceTab targetValue={target.value} />}
      {tab === 'activity' && <ActivityTab targetId={id} />}
      {tab === 'settings' && <SettingsTab target={target} onArchive={() => archive.mutate()} />}
      <NewScanDialog open={newScanOpen} onClose={() => setNewScanOpen(false)} target={target} />
    </div>
  );
}
