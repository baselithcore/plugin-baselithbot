/**
 * Self-service "LLM Usage" panel — the signed-in user's month-to-date spend
 * against their effective monthly cap, with a progress bar and a warn/block
 * banner once they cross the threshold.
 */

import { useEffect, useState } from 'react';
import { TrendingUp, AlertTriangle, Ban } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { getMyLlmUsage, type MyLlmUsage } from '../../api/account';
import { useAuth } from '../../hooks/useAuthContext';

const STATUS_COLOR: Record<string, string> = {
  ok: 'var(--admin-success, #15803d)',
  warning: 'var(--admin-warning, #b45309)',
  blocked: 'var(--admin-danger, #be123c)',
};

function money(n: number): string {
  return `$${n.toFixed(n < 0.01 && n > 0 ? 4 : 2)}`;
}

export default function UsagePanel() {
  const { t } = useTranslation();
  const { accessToken } = useAuth();
  const [usage, setUsage] = useState<MyLlmUsage | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!accessToken) return;
    getMyLlmUsage(accessToken)
      .then(setUsage)
      .catch((e) => setError(e instanceof Error ? e.message : 'Error'));
  }, [accessToken]);

  if (error) return <div className="acct-alert acct-alert-error">{error}</div>;
  if (!usage) return <div className="acct-panel">{t('account.usage.loading')}</div>;

  const uncapped = usage.cap_usd == null;
  const pct = usage.percent_used ?? 0;
  const color = STATUS_COLOR[usage.status] ?? STATUS_COLOR.ok;

  return (
    <div className="acct-panel">
      <h3 className="acct-panel-title">
        <TrendingUp size={18} /> {t('account.usage.title')}
      </h3>
      <p className="acct-panel-sub">{t('account.usage.subtitle')}</p>

      {/* Status banner */}
      {usage.status === 'blocked' && (
        <div className="acct-alert acct-alert-error" style={{ display: 'flex', gap: 8 }}>
          <Ban size={16} />
          {usage.enforce ? t('account.usage.blocked') : t('account.usage.over')}
        </div>
      )}
      {usage.status === 'warning' && (
        <div className="acct-alert" style={{ display: 'flex', gap: 8, color }}>
          <AlertTriangle size={16} />
          {t('account.usage.warning', { pct })}
        </div>
      )}

      {/* Spend figures */}
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, margin: '14px 0 8px' }}>
        <span style={{ fontSize: 28, fontWeight: 700, color }}>{money(usage.spend_usd)}</span>
        <span style={{ opacity: 0.7 }}>
          {uncapped
            ? t('account.usage.uncapped')
            : t('account.usage.of_cap', { cap: money(usage.cap_usd ?? 0) })}
        </span>
      </div>

      {/* Progress bar (only when capped) */}
      {!uncapped && (
        <div
          aria-label={t('account.usage.progress', { pct })}
          style={{
            height: 10,
            borderRadius: 999,
            background: 'var(--admin-border, rgba(127,127,127,.2))',
            overflow: 'hidden',
          }}
        >
          <div
            style={{
              width: `${Math.min(pct, 100)}%`,
              height: '100%',
              background: color,
              transition: 'width .3s ease',
            }}
          />
        </div>
      )}

      <p className="acct-panel-sub" style={{ marginTop: 12 }}>
        {t('account.usage.reset_note', { period: usage.period })}
      </p>
    </div>
  );
}
