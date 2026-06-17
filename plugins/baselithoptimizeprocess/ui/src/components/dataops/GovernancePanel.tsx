import { useCallback, useEffect, useState } from 'react';

import { api } from '../../api/client';
import type { AppliedChange, AuditEvent, ProcessVersion } from '../../api/types';

const ACTION_LABEL: Record<string, string> = {
  process_register: 'Registered',
  process_import: 'Imported',
  process_mine: 'Mined',
  process_delete: 'Deleted',
  proposal_approve: 'Approved proposal',
  proposal_reject: 'Rejected proposal',
  rule_create: 'Created rule',
  rule_delete: 'Deleted rule',
  optimize_run: 'Ran optimizer',
  process_apply: 'Applied change',
  process_rollback: 'Rolled back',
};

const CHANGE_CHIP: Record<string, string> = {
  active: 'bg-accent/15 text-accent-soft',
  monitoring: 'bg-sev-medium/15 text-sev-medium',
  kept: 'bg-sev-low/15 text-sev-low',
  rolled_back: 'bg-slate-500/15 text-slate-400',
};

const dateTime = new Intl.DateTimeFormat(undefined, {
  dateStyle: 'medium',
  timeStyle: 'short',
});

function when(iso: string): string {
  try {
    return dateTime.format(new Date(iso));
  } catch {
    return iso;
  }
}

/** Governance view: version history, applied changes (rollback), audit trail. */
export function GovernancePanel({ processId }: { processId: string }) {
  const [versions, setVersions] = useState<ProcessVersion[]>([]);
  const [changes, setChanges] = useState<AppliedChange[]>([]);
  const [audit, setAudit] = useState<AuditEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const load = useCallback(() => {
    Promise.all([
      api.listVersions(processId),
      api.listChanges(processId),
      api.processAudit(processId),
    ])
      .then(([v, c, a]) => {
        setVersions(v);
        setChanges(c);
        setAudit(a);
      })
      .catch((e) => setError(e instanceof Error ? e.message : 'Load failed'));
  }, [processId]);

  useEffect(() => load(), [load]);

  async function rollbackChange(id: string) {
    if (!window.confirm('Rollback this applied change?')) return;
    setBusy(id);
    setError(null);
    try {
      await api.rollbackChange(id);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Rollback failed');
    } finally {
      setBusy(null);
    }
  }

  async function rollbackVersion(version: number) {
    if (!window.confirm(`Restore process version v${version}?`)) return;
    setBusy(`v${version}`);
    setError(null);
    try {
      await api.rollbackToVersion(processId, version);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Rollback failed');
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-5">
      {error && <p className="text-sm text-sev-critical">{error}</p>}

      {changes.length > 0 && (
        <section>
          <h2 className="mb-2 text-sm font-semibold text-slate-200">Applied Changes</h2>
          <ul className="space-y-2">
            {changes.map((c) => (
              <li key={c.id} className="glass flex items-center gap-3 p-3">
                <span className={`chip shrink-0 ${CHANGE_CHIP[c.status] ?? ''}`}>{c.status}</span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm text-slate-300">{c.detail || c.id}</p>
                  <p className="text-[11px] text-slate-500">
                    v{c.from_version ?? '—'} → v{c.to_version} · {c.applied_by} ·{' '}
                    {when(c.applied_at)}
                    {c.guard && ` · guard ${c.guard.kpi_id} ±${c.guard.max_regression_pct}%`}
                  </p>
                </div>
                {c.status !== 'rolled_back' && (
                  <button
                    className="btn-ghost shrink-0 text-xs"
                    disabled={busy === c.id}
                    onClick={() => rollbackChange(c.id)}
                  >
                    {busy === c.id ? '…' : 'Rollback'}
                  </button>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <section>
          <h2 className="mb-2 text-sm font-semibold text-slate-200">Version History</h2>
          {versions.length === 0 ? (
            <p className="text-sm text-slate-500">No versions yet.</p>
          ) : (
            <ul className="space-y-2">
              {versions.map((v, i) => (
                <li key={v.version} className="glass p-3">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-mono text-sm text-accent-soft">v{v.version}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-[11px] text-slate-500">{when(v.created_at)}</span>
                      {i > 0 && (
                        <button
                          className="btn-ghost text-[11px]"
                          disabled={busy === `v${v.version}`}
                          onClick={() => rollbackVersion(v.version)}
                        >
                          {busy === `v${v.version}` ? '…' : 'Restore'}
                        </button>
                      )}
                    </div>
                  </div>
                  <p className="mt-1 text-sm text-slate-300">{v.summary}</p>
                  <p className="mt-0.5 text-[11px] text-slate-500">
                    by <span className="font-mono">{v.actor}</span> · {v.graph.nodes.length} steps
                  </p>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section>
          <h2 className="mb-2 text-sm font-semibold text-slate-200">Audit Trail</h2>
          {audit.length === 0 ? (
            <p className="text-sm text-slate-500">No audit events yet.</p>
          ) : (
            <ul className="space-y-2">
              {audit.map((e) => (
                <li key={e.id} className="glass flex items-start gap-3 p-3">
                  <span className="chip mt-0.5 shrink-0 bg-white/5 text-slate-300">
                    {ACTION_LABEL[e.action] ?? e.action}
                  </span>
                  <div className="min-w-0">
                    <p className="text-sm text-slate-300">{e.detail || e.target_id}</p>
                    <p className="mt-0.5 text-[11px] text-slate-500">
                      <span className="font-mono">{e.actor}</span> · {when(e.created_at)}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </div>
  );
}
