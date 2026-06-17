import { useCallback, useEffect, useState } from 'react';

import { api } from '../../api/client';
import type {
  ActionType,
  AutomationRule,
  ProcessGraph,
  RuleFiring,
  TriggerType,
} from '../../api/types';
import { timeAgo } from '../../lib/ui';

/** Manage automation rules (condition→action) and watch their firings. */
export function AutomationPanel({ process }: { process: ProcessGraph }) {
  const [rules, setRules] = useState<AutomationRule[]>([]);
  const [firings, setFirings] = useState<RuleFiring[]>([]);

  const refresh = useCallback(async () => {
    const [r, f] = await Promise.all([
      api.listRules(process.id).catch(() => []),
      api.listFirings(process.id).catch(() => []),
    ]);
    setRules(r);
    setFirings([...f].reverse());
  }, [process.id]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return (
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1fr)_24rem]">
      <div className="space-y-4">
        <RuleForm process={process} onCreated={refresh} />
        <div>
          <h2 className="mb-2 text-sm font-semibold text-slate-200">Rules</h2>
          {rules.length === 0 ? (
            <div className="glass p-4 text-sm text-slate-500">No automation rules yet.</div>
          ) : (
            <ul className="space-y-2">
              {rules.map((r) => (
                <li key={r.id} className="glass flex items-center justify-between p-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium text-slate-100">{r.name}</p>
                    <p className="truncate text-[11px] text-slate-500">
                      {describeTrigger(r)} → {r.action.type}
                    </p>
                  </div>
                  <button
                    className="btn-ghost px-2 py-1 text-xs text-sev-critical/80"
                    onClick={async () => {
                      if (!window.confirm(`Delete rule "${r.name}"?`)) return;
                      await api.deleteRule(r.id);
                      void refresh();
                    }}
                    aria-label={`Delete rule ${r.name}`}
                  >
                    Delete
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div>
        <h2 className="mb-2 text-sm font-semibold text-slate-200">Recent Firings</h2>
        {firings.length === 0 ? (
          <div className="glass p-4 text-sm text-slate-500">No firings recorded.</div>
        ) : (
          <ul className="space-y-2">
            {firings.map((f, i) => (
              <li key={i} className="glass p-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-accent-soft">{f.rule_name}</span>
                  <span className="text-[11px] text-slate-500">{timeAgo(f.fired_at)}</span>
                </div>
                <p className="mt-0.5 text-xs text-slate-400">{f.detail}</p>
                <span className="chip mt-1 bg-white/5 text-slate-400">{f.action_type}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function describeTrigger(rule: AutomationRule): string {
  if (rule.trigger.type === 'kpi_breach') return `KPI ${rule.trigger.kpi_id} breaches`;
  if (rule.trigger.type === 'predicted_breach')
    return `KPI ${rule.trigger.kpi_id} forecast to breach`;
  return `bottleneck ≥ ${rule.trigger.min_severity}`;
}

function RuleForm({ process, onCreated }: { process: ProcessGraph; onCreated: () => void }) {
  const [name, setName] = useState('');
  const [triggerType, setTriggerType] = useState<TriggerType>('kpi_breach');
  const [kpiId, setKpiId] = useState(process.kpis[0]?.id ?? '');
  const [minSeverity, setMinSeverity] = useState('high');
  const [actionType, setActionType] = useState<ActionType>('alert');
  const [busy, setBusy] = useState(false);

  async function create() {
    if (!name) return;
    setBusy(true);
    try {
      await api.createRule(
        process.id,
        name,
        { type: triggerType, kpi_id: kpiId, min_severity: minSeverity },
        { type: actionType, message: '', webhook_url: '' }
      );
      setName('');
      onCreated();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="glass space-y-2 p-4">
      <div>
        <h2 className="text-sm font-semibold text-slate-100">New Rule</h2>
        <p className="mt-1 text-xs text-slate-500">
          Trigger alerts, optimizer runs or webhooks from KPI signals.
        </p>
      </div>
      <label className="block text-[11px] font-medium text-slate-400">
        Rule Name
        <input
          className="field mt-1"
          name="rule-name"
          autoComplete="off"
          placeholder="Critical SLA breach"
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </label>
      <div className="grid grid-cols-2 gap-2">
        <label className="block text-[11px] font-medium text-slate-400">
          Trigger
          <select
            className="field mt-1"
            name="rule-trigger"
            value={triggerType}
            onChange={(e) => setTriggerType(e.target.value as TriggerType)}
          >
            <option value="kpi_breach">When KPI breaches</option>
            <option value="predicted_breach">When KPI forecast to breach</option>
            <option value="bottleneck_severity">When bottleneck &gt;=</option>
          </select>
        </label>
        {triggerType !== 'bottleneck_severity' ? (
          <label className="block text-[11px] font-medium text-slate-400">
            KPI
            <select
              className="field mt-1"
              name="rule-kpi"
              value={kpiId}
              onChange={(e) => setKpiId(e.target.value)}
            >
              {process.kpis.map((k) => (
                <option key={k.id} value={k.id}>
                  {k.name}
                </option>
              ))}
            </select>
          </label>
        ) : (
          <label className="block text-[11px] font-medium text-slate-400">
            Severity
            <select
              className="field mt-1"
              name="rule-severity"
              value={minSeverity}
              onChange={(e) => setMinSeverity(e.target.value)}
            >
              {['low', 'medium', 'high', 'critical'].map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>
      <label className="block text-[11px] font-medium text-slate-400">
        Action
        <select
          className="field mt-1"
          name="rule-action"
          value={actionType}
          onChange={(e) => setActionType(e.target.value as ActionType)}
        >
          <option value="alert">Then: raise alert</option>
          <option value="recommend_optimization">Then: run optimizer</option>
          <option value="webhook">Then: call webhook</option>
        </select>
      </label>
      <button
        className="btn-primary w-full justify-center"
        onClick={create}
        disabled={busy || !name}
      >
        {busy ? 'Creating…' : 'Add Rule'}
      </button>
    </div>
  );
}
