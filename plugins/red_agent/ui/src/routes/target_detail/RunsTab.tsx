import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  api,
  type Finding,
  type RunDiff,
  type ScanRow,
  type ScanStatus,
  type TargetRecord,
} from '../../lib/api';
import {
  Button,
  Card,
  Chip,
  ConfirmDialog,
  EmptyState,
  FindingDetailModal,
  Icon,
  MenuItem,
  Popover,
  SeverityBadge,
  StatusBadge,
} from '../../components/ui';
import { relTime } from './_utils';
import { NewScanDialog } from './NewScanDialog';

const TERMINAL_SCAN_STATES: ScanStatus[] = ['completed', 'failed', 'cancelled'];

export function RunsTab({
  target,
  runs,
  loading,
}: {
  target: TargetRecord;
  runs: ScanRow[];
  loading: boolean;
}) {
  const targetId = target.id;
  const completed = useMemo(() => runs.filter((r) => r.status === 'completed'), [runs]);
  const [baseline, setBaseline] = useState<string>('');
  const [latest, setLatest] = useState<string>('');
  const [selected, setSelected] = useState<Finding | null>(null);
  const [confirmDelete, setConfirmDelete] = useState<ScanRow | null>(null);
  const [newScanOpen, setNewScanOpen] = useState(false);
  const qc = useQueryClient();
  const remove = useMutation({
    mutationFn: (id: string) => api.deleteScan(id),
    onSuccess: () => {
      setConfirmDelete(null);
      qc.invalidateQueries({ queryKey: ['target-runs', targetId] });
      qc.invalidateQueries({ queryKey: ['target-findings', targetId] });
      qc.invalidateQueries({ queryKey: ['target-posture', targetId] });
    },
  });

  // Auto-pick: oldest completed = baseline, newest completed = latest.
  const autoBaseline = completed.at(-1)?.id ?? '';
  const autoLatest = completed[0]?.id ?? '';
  const effBaseline = baseline || autoBaseline;
  const effLatest = latest || autoLatest;

  const diffQ = useQuery({
    queryKey: ['target-diff', targetId, effBaseline, effLatest],
    queryFn: () => api.diffRuns(targetId, effBaseline, effLatest),
    enabled: Boolean(effBaseline && effLatest && effBaseline !== effLatest),
  });

  if (loading) return <div className="text-sm text-text-muted">Loading…</div>;
  if (runs.length === 0)
    return (
      <>
        <Card>
          <EmptyState
            icon={<Icon.Scans size={20} />}
            title="No runs yet"
            description="Configure scanners and intensity, then launch the first scan."
            action={
              <Button variant="primary" onClick={() => setNewScanOpen(true)}>
                <Icon.Bolt size={14} />
                New scan
              </Button>
            }
          />
        </Card>
        <NewScanDialog open={newScanOpen} onClose={() => setNewScanOpen(false)} target={target} />
      </>
    );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-2xs font-mono uppercase tracking-wider text-text-muted">
          {runs.length} run{runs.length === 1 ? '' : 's'}
        </div>
        <Button variant="primary" onClick={() => setNewScanOpen(true)}>
          <Icon.Bolt size={14} />
          New scan
        </Button>
      </div>
      {completed.length >= 2 && (
        <Card
          title="Compare runs"
          subtitle="Diff baseline vs latest to surface regressions and fixes"
        >
          <div className="flex flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              <span className="text-2xs font-mono uppercase tracking-wider text-text-muted">
                baseline
              </span>
              <select
                value={effBaseline}
                onChange={(e) => setBaseline(e.target.value)}
                className="ra-select"
              >
                {completed.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.id.slice(0, 8)} — {relTime(r.started_at)}
                  </option>
                ))}
              </select>
            </div>
            <Icon.ArrowRight size={14} className="text-text-muted" />
            <div className="flex items-center gap-2">
              <span className="text-2xs font-mono uppercase tracking-wider text-text-muted">
                latest
              </span>
              <select
                value={effLatest}
                onChange={(e) => setLatest(e.target.value)}
                className="ra-select"
              >
                {completed.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.id.slice(0, 8)} — {relTime(r.started_at)}
                  </option>
                ))}
              </select>
            </div>
          </div>
          {diffQ.data && <DiffSummary diff={diffQ.data} onSelect={setSelected} />}
          {diffQ.error && (
            <p className="mt-3 rounded border border-sev-critical/40 bg-sev-critical/10 px-3 py-2 text-sm text-sev-critical">
              {String(diffQ.error)}
            </p>
          )}
        </Card>
      )}

      <Card padded={false}>
        <table className="ra-table">
          <thead>
            <tr>
              <th>Run</th>
              <th className="w-32">Status</th>
              <th className="w-28">Intensity</th>
              <th className="w-32">Started</th>
              <th>Scanners</th>
              <th className="w-10" aria-hidden="true" />
            </tr>
          </thead>
          <tbody>
            {runs.map((r) => {
              const terminal = TERMINAL_SCAN_STATES.includes(r.status);
              return (
                <tr key={r.id}>
                  <td>
                    <Link to={`/scans/${r.id}`} className="font-mono text-text-primary">
                      {r.id.slice(0, 8)}
                    </Link>
                  </td>
                  <td>
                    <StatusBadge status={r.status} />
                  </td>
                  <td>
                    <Chip>{r.intensity}</Chip>
                  </td>
                  <td className="font-mono text-xs text-text-muted">{relTime(r.started_at)}</td>
                  <td>
                    <div className="flex flex-wrap gap-1">
                      {r.scanners.map((s) => (
                        <Chip key={s}>{s}</Chip>
                      ))}
                    </div>
                  </td>
                  <td>
                    <Popover
                      align="right"
                      width={220}
                      trigger={
                        <button
                          type="button"
                          aria-label="Run actions"
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
                            label="Delete run"
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
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>
      <FindingDetailModal
        finding={selected}
        open={selected !== null}
        onClose={() => setSelected(null)}
      />
      <NewScanDialog open={newScanOpen} onClose={() => setNewScanOpen(false)} target={target} />
      <ConfirmDialog
        open={confirmDelete !== null}
        onClose={() => setConfirmDelete(null)}
        onConfirm={() => (confirmDelete ? remove.mutateAsync(confirmDelete.id) : Promise.resolve())}
        title="Delete run permanently?"
        description={
          confirmDelete && (
            <>
              Run{' '}
              <span className="font-mono text-text-primary">{confirmDelete.id.slice(0, 8)}</span>{' '}
              and all of its findings will be removed from this target's history.
            </>
          )
        }
        consequences={[
          'All findings discovered in this run will be deleted.',
          'Diff baselines pointing to this run will be invalidated.',
          'Audit log entries are preserved for compliance.',
        ]}
        acknowledgement="I understand this run and its findings will be permanently deleted."
        confirmLabel="Delete forever"
        tone="danger"
        busy={remove.isPending}
      />
    </div>
  );
}

function DiffSummary({ diff, onSelect }: { diff: RunDiff; onSelect: (f: Finding) => void }) {
  return (
    <div className="mt-4 space-y-3">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <DiffStat
          label="New"
          value={diff.new.length}
          tone="critical"
          icon={<Icon.ArrowUp size={12} />}
        />
        <DiffStat
          label="Regressed"
          value={diff.regressed.length}
          tone="warn"
          icon={<Icon.TrendUp size={12} />}
        />
        <DiffStat
          label="Fixed"
          value={diff.fixed.length}
          tone="success"
          icon={<Icon.Check size={12} />}
        />
        <DiffStat
          label="Unchanged"
          value={diff.unchanged}
          tone="neutral"
          icon={<Icon.Activity size={12} />}
        />
      </div>
      {diff.new.length > 0 && (
        <DiffList title="New findings" tone="critical" findings={diff.new} onSelect={onSelect} />
      )}
      {diff.regressed.length > 0 && (
        <div>
          <h4 className="mb-2 text-xs font-mono uppercase tracking-wider text-accent-warn">
            Regressed
          </h4>
          <ul className="divide-y divide-bg-line/60 rounded-md border border-bg-line">
            {diff.regressed.map((r) => (
              <li key={r.finding.id}>
                <button
                  type="button"
                  onClick={() => onSelect(r.finding)}
                  className="flex w-full items-center justify-between gap-3 px-3 py-2 text-sm text-left transition-colors hover:bg-bg-hover/50"
                >
                  <div className="min-w-0">
                    <div className="truncate text-text-primary">{r.finding.title}</div>
                    <div className="font-mono text-2xs text-text-muted">
                      {r.finding.endpoint ?? r.finding.target}
                    </div>
                  </div>
                  <span className="font-mono text-2xs uppercase">
                    <span className="text-text-muted">{r.from_severity}</span>
                    <span className="px-1 text-text-subtle">→</span>
                    <SeverityBadge severity={r.to_severity} full />
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
      {diff.fixed.length > 0 && (
        <DiffList
          title="Fixed (no longer present)"
          tone="success"
          findings={diff.fixed}
          onSelect={onSelect}
        />
      )}
    </div>
  );
}

function DiffStat({
  label,
  value,
  tone,
  icon,
}: {
  label: string;
  value: number;
  tone: 'critical' | 'warn' | 'success' | 'neutral';
  icon: React.ReactNode;
}) {
  const cls =
    tone === 'critical'
      ? 'text-sev-critical bg-sev-critical/10 ring-sev-critical/30'
      : tone === 'warn'
        ? 'text-accent-warn bg-accent-warn/10 ring-accent-warn/30'
        : tone === 'success'
          ? 'text-status-success bg-status-success/10 ring-status-success/30'
          : 'text-text-secondary bg-bg-overlay ring-bg-line';
  return (
    <div className={`rounded-md p-3 ring-1 ${cls}`}>
      <div className="flex items-center gap-1.5 text-2xs font-mono uppercase tracking-wider opacity-80">
        {icon}
        {label}
      </div>
      <div className="mt-1 font-display text-xl font-medium tabular-nums">{value}</div>
    </div>
  );
}

function DiffList({
  title,
  tone,
  findings,
  onSelect,
}: {
  title: string;
  tone: 'critical' | 'success';
  findings: Finding[];
  onSelect: (f: Finding) => void;
}) {
  const titleCls = tone === 'critical' ? 'text-sev-critical' : 'text-status-success';
  return (
    <div>
      <h4 className={`mb-2 text-xs font-mono uppercase tracking-wider ${titleCls}`}>
        {title} <span className="text-text-muted">· {findings.length}</span>
      </h4>
      <ul className="divide-y divide-bg-line/60 rounded-md border border-bg-line max-h-[420px] overflow-y-auto">
        {findings.map((f) => (
          <li key={f.id}>
            <button
              type="button"
              onClick={() => onSelect(f)}
              className="flex w-full items-center justify-between gap-3 px-3 py-2 text-sm text-left transition-colors hover:bg-bg-hover/50"
            >
              <div className="min-w-0">
                <div className="truncate text-text-primary">{f.title}</div>
                <div className="font-mono text-2xs text-text-muted">{f.endpoint ?? f.target}</div>
              </div>
              <SeverityBadge severity={f.severity} full />
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
