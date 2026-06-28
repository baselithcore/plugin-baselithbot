/**
 * Budget tab — org-wide LLM cost policy + per-user monthly spend & caps.
 *
 * Top: the global default cap, warn threshold, and enforcement toggle.
 * Below: month-to-date spend per user with an inline cap override and a reset.
 */

import { useEffect, useState } from 'react';
import { CreditCard, Save, RotateCcw, AlertTriangle, Ban } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import {
  getCostPolicy,
  getUsageOverview,
  setCostPolicy,
  setUserCap,
  resetUserUsage,
  type CostPolicy,
  type AdminUsage,
  type UsageStatus,
} from '../../api/cost';

const STATUS_COLOR: Record<UsageStatus, string> = {
  ok: 'var(--admin-success, #15803d)',
  warning: 'var(--admin-warning, #b45309)',
  blocked: 'var(--admin-danger, #be123c)',
};

const money = (n: number) => `$${n.toFixed(n > 0 && n < 0.01 ? 4 : 2)}`;
const num = (v: string): number | null => (v.trim() === '' ? null : Math.max(0, Number(v) || 0));

export default function BudgetTab() {
  const { t } = useTranslation();
  const [policy, setPolicy] = useState<CostPolicy | null>(null);
  const [usage, setUsage] = useState<AdminUsage | null>(null);
  const [caps, setCaps] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState('');

  const reloadUsage = () =>
    getUsageOverview()
      .then((u) => {
        setUsage(u);
        const next: Record<string, string> = {};
        u.rows.forEach((r) => (next[r.user_id] = r.user_cap_usd?.toString() ?? ''));
        setCaps(next);
      })
      .catch((e) => setMsg(e.message));

  useEffect(() => {
    getCostPolicy().then(setPolicy).catch((e) => setMsg(e.message));
    reloadUsage();
  }, []);

  const savePolicy = async () => {
    if (!policy) return;
    try {
      setPolicy(await setCostPolicy(policy));
      setMsg(t('budget.saved'));
    } catch (e) {
      setMsg(e instanceof Error ? e.message : 'Error');
    }
  };

  const saveCap = async (userId: string) => {
    try {
      await setUserCap(userId, num(caps[userId] ?? ''));
      await reloadUsage();
      setMsg(t('budget.cap_saved'));
    } catch (e) {
      setMsg(e instanceof Error ? e.message : 'Error');
    }
  };

  const reset = async (userId: string) => {
    if (!window.confirm(t('budget.confirm_reset'))) return;
    await resetUserUsage(userId).catch((e) => setMsg(e.message));
    await reloadUsage();
  };

  return (
    <div className="admin-tab-content">
      <div className="admin-section-header">
        <h2>
          <CreditCard size={20} /> {t('budget.title')}
        </h2>
        <p>{t('budget.description')}</p>
      </div>

      {msg && <div className="admin-alert">{msg}</div>}

      {/* Global policy */}
      {policy && (
        <div className="admin-card" style={{ padding: 16, marginBottom: 18 }}>
          <h3 style={{ marginTop: 0 }}>{t('budget.global_policy')}</h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 18, alignItems: 'flex-end' }}>
            <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <span style={{ fontSize: 12, opacity: 0.8 }}>{t('budget.default_cap')}</span>
              <input
                type="number"
                min={0}
                step="0.01"
                placeholder={t('budget.unlimited')}
                value={policy.monthly_cap_usd ?? ''}
                onChange={(e) =>
                  setPolicy({ ...policy, monthly_cap_usd: num(e.target.value) })
                }
                className="admin-input"
                style={{ width: 140 }}
              />
            </label>
            <label style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
              <span style={{ fontSize: 12, opacity: 0.8 }}>{t('budget.warn_threshold')}</span>
              <input
                type="number"
                min={1}
                max={100}
                value={policy.warn_threshold_pct}
                onChange={(e) =>
                  setPolicy({ ...policy, warn_threshold_pct: Number(e.target.value) || 80 })
                }
                className="admin-input"
                style={{ width: 100 }}
              />
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <input
                type="checkbox"
                checked={policy.enforce}
                onChange={(e) => setPolicy({ ...policy, enforce: e.target.checked })}
              />
              <span>{t('budget.enforce')}</span>
            </label>
            <button className="admin-btn admin-btn-primary" onClick={savePolicy}>
              <Save size={15} /> {t('budget.save')}
            </button>
          </div>
          <p style={{ fontSize: 12, opacity: 0.7, marginBottom: 0 }}>{t('budget.policy_note')}</p>
        </div>
      )}

      {/* Per-user usage */}
      <div className="admin-card" style={{ padding: 0, overflow: 'hidden' }}>
        <table className="admin-table" style={{ width: '100%' }}>
          <thead>
            <tr>
              <th>{t('budget.col_user')}</th>
              <th>{t('budget.col_spend')}</th>
              <th>{t('budget.col_status')}</th>
              <th>{t('budget.col_user_cap')}</th>
              <th style={{ textAlign: 'right' }}>{t('budget.col_actions')}</th>
            </tr>
          </thead>
          <tbody>
            {(usage?.rows ?? []).map((r) => (
              <tr key={r.user_id}>
                <td>{r.email || r.username || r.user_id}</td>
                <td>
                  {money(r.spend_usd)}
                  {r.cap_usd != null && (
                    <span style={{ opacity: 0.6 }}> / {money(r.cap_usd)}</span>
                  )}
                </td>
                <td>
                  <span
                    style={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 4,
                      color: STATUS_COLOR[r.status],
                      fontWeight: 600,
                      fontSize: 12,
                    }}
                  >
                    {r.status === 'blocked' && <Ban size={13} />}
                    {r.status === 'warning' && <AlertTriangle size={13} />}
                    {r.percent_used != null ? `${r.percent_used}%` : t('budget.uncapped')}
                  </span>
                </td>
                <td>
                  <input
                    type="number"
                    min={0}
                    step="0.01"
                    placeholder={t('budget.inherit')}
                    value={caps[r.user_id] ?? ''}
                    onChange={(e) => setCaps({ ...caps, [r.user_id]: e.target.value })}
                    className="admin-input"
                    style={{ width: 110 }}
                  />
                </td>
                <td style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
                  <button
                    className="admin-btn admin-btn-ghost admin-btn-sm"
                    onClick={() => saveCap(r.user_id)}
                  >
                    {t('budget.set')}
                  </button>
                  <button
                    className="admin-btn admin-btn-ghost admin-btn-sm"
                    onClick={() => reset(r.user_id)}
                    title={t('budget.reset')}
                  >
                    <RotateCcw size={14} />
                  </button>
                </td>
              </tr>
            ))}
            {usage && usage.rows.length === 0 && (
              <tr>
                <td colSpan={5} style={{ textAlign: 'center', padding: 24, opacity: 0.7 }}>
                  {t('budget.empty')}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
