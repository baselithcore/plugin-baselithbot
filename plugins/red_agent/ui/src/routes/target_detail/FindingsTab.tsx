import { useMemo, useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { api, type Finding, type FindingState } from '../../lib/api';
import { Card, EmptyState, FindingDetailModal, Icon, SeverityBadge } from '../../components/ui';
import { relTime } from './_utils';

export function FindingsTab({
  targetId,
  findings,
  loading,
  onUpdate,
}: {
  targetId: string;
  findings: Finding[];
  loading: boolean;
  onUpdate: () => void;
}) {
  const [stateFilter, setStateFilter] = useState<FindingState | 'all'>('all');
  const [selected, setSelected] = useState<Finding | null>(null);
  const visible = useMemo(
    () => (stateFilter === 'all' ? findings : findings.filter((f) => f.state === stateFilter)),
    [findings, stateFilter]
  );
  const update = useMutation({
    mutationFn: (vars: { id: string; state: FindingState }) =>
      api.updateFinding(vars.id, { state: vars.state }),
    onSuccess: onUpdate,
  });

  const states: (FindingState | 'all')[] = [
    'all',
    'open',
    'triaged',
    'fixed',
    'wontfix',
    'accepted',
  ];
  if (loading) return <div className="text-sm text-text-muted">Loading findings…</div>;
  return (
    <Card padded={false}>
      <div className="flex flex-wrap items-center gap-2 border-b border-bg-line p-3">
        {states.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => setStateFilter(s)}
            className={`rounded-md px-2.5 py-1 text-xs font-mono capitalize transition-colors ${
              stateFilter === s
                ? 'bg-brand/10 text-brand ring-1 ring-brand/30'
                : 'text-text-muted hover:bg-bg-overlay hover:text-text-primary'
            }`}
          >
            {s} ({s === 'all' ? findings.length : findings.filter((f) => f.state === s).length})
          </button>
        ))}
        <span className="ml-auto text-2xs text-text-muted">target {targetId.slice(0, 8)}</span>
      </div>
      {visible.length === 0 ? (
        <EmptyState compact icon={<Icon.ShieldCheck size={20} />} title="Nothing to triage" />
      ) : (
        <table className="ra-table">
          <thead>
            <tr>
              <th className="w-24">Severity</th>
              <th>Finding</th>
              <th className="w-20 text-right">Risk</th>
              <th className="w-24">State</th>
              <th className="w-24">Due</th>
              <th className="w-44">Triage</th>
            </tr>
          </thead>
          <tbody>
            {visible.map((f) => (
              <tr
                key={f.id}
                onClick={() => setSelected(f)}
                className="cursor-pointer transition-colors hover:bg-bg-hover/50"
              >
                <td>
                  <SeverityBadge severity={f.severity} full />
                </td>
                <td>
                  <div className="font-medium text-text-primary">{f.title}</div>
                  <div className="font-mono text-xs text-text-muted">{f.endpoint ?? f.target}</div>
                </td>
                <td className="text-right font-mono tabular-nums text-text-secondary">
                  {f.risk_score != null && Number.isFinite(f.risk_score)
                    ? f.risk_score.toFixed(1)
                    : '—'}
                </td>
                <td>
                  <span className="font-mono text-xs capitalize text-text-secondary">
                    {f.state}
                  </span>
                </td>
                <td className="font-mono text-xs text-text-muted">
                  {f.due_at ? relTime(f.due_at) : '—'}
                </td>
                <td onClick={(e) => e.stopPropagation()}>
                  <select
                    value={f.state}
                    onChange={(e) =>
                      update.mutate({ id: f.id, state: e.target.value as FindingState })
                    }
                    className="ra-select ra-select-sm"
                  >
                    {(['open', 'triaged', 'fixed', 'wontfix', 'accepted'] as FindingState[]).map(
                      (s) => (
                        <option key={s} value={s}>
                          {s}
                        </option>
                      )
                    )}
                  </select>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <FindingDetailModal
        finding={selected}
        open={selected !== null}
        onClose={() => setSelected(null)}
      />
    </Card>
  );
}
