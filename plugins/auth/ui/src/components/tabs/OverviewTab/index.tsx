/**
 * Overview — the console landing page. A glanceable identity-and-activity
 * dashboard: KPI cards, a 14-day activity spark, MFA adoption, role mix, AI
 * usage, and the latest audit events. All data is aggregated client-side from
 * the existing admin endpoints (see ./hooks), so no new backend is required.
 */

import { useTranslation } from 'react-i18next';
import {
  LayoutDashboard,
  Users,
  KeyRound,
  ShieldCheck,
  Activity,
  Coins,
  RefreshCw,
} from 'lucide-react';
import PageHeader from '../../shared/PageHeader';
import StatCards, { type Stat } from './StatCards';
import OverviewCharts from './OverviewCharts';
import { useOverview } from './hooks';
import { OVERVIEW_STYLES } from './styles';

const OverviewTab = () => {
  const { t } = useTranslation();
  const { data, loading, error, reload } = useOverview();

  const stats: Stat[] = data
    ? [
        {
          key: 'users',
          icon: Users,
          label: t('overview.kpi.users'),
          value: String(data.totalUsers),
          hint: t('overview.kpi.usersHint', { active: data.activeUsers }),
        },
        {
          key: 'sessions',
          icon: KeyRound,
          label: t('overview.kpi.sessions'),
          value: String(data.activeSessions),
        },
        {
          key: 'mfa',
          icon: ShieldCheck,
          label: t('overview.kpi.mfa'),
          value: `${data.mfa.pct}%`,
          tone: data.mfa.pct >= 50 ? 'success' : 'warning',
        },
        {
          key: 'events',
          icon: Activity,
          label: t('overview.kpi.events'),
          value: String(data.eventsToday),
        },
        ...(data.usage
          ? [
              {
                key: 'spend',
                icon: Coins,
                label: t('overview.kpi.spend'),
                value: `$${data.usage.totalSpend.toFixed(2)}`,
              } as Stat,
            ]
          : []),
      ]
    : [];

  return (
    <div className="ov">
      <PageHeader
        icon={<LayoutDashboard size={20} />}
        title={t('overview.title')}
        subtitle={t('overview.subtitle')}
        actions={
          <button
            type="button"
            className="admin-btn admin-btn-secondary admin-btn-sm"
            onClick={reload}
            disabled={loading}
          >
            <RefreshCw size={14} /> {t('overview.refresh')}
          </button>
        }
      />

      {loading && !data && (
        <div className="ov-loading">
          <span className="admin-spinner-lg" />
        </div>
      )}
      {error && <div className="admin-alert admin-alert-error">{t('overview.error')}</div>}

      {data && (
        <>
          <StatCards stats={stats} />
          <OverviewCharts data={data} />
          <section className="admin-card ov-card ov-recent">
            <header className="ov-card-head">
              <h3>{t('overview.recent.title')}</h3>
            </header>
            {data.recent.length ? (
              <ul className="ov-recent-list">
                {data.recent.map((e) => (
                  <li key={e.id}>
                    <span className="ov-recent-action">{e.action}</span>
                    <span className="ov-recent-meta mono">{e.actor_id?.slice(0, 8) || '—'}</span>
                    <time className="ov-recent-time">
                      {e.created_at ? new Date(e.created_at).toLocaleString() : ''}
                    </time>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="ov-empty">{t('overview.recent.empty')}</p>
            )}
          </section>
        </>
      )}

      <style>{OVERVIEW_STYLES}</style>
    </div>
  );
};

export default OverviewTab;
