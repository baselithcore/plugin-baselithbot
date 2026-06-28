/**
 * Overview — the console landing page. A restrained operations view: a KPI
 * strip, a 14-day activity trend, security posture, role mix, AI usage and the
 * latest audit events. All data is aggregated client-side from the existing
 * admin endpoints (see ./hooks), so no new backend is required.
 */

import { useTranslation } from 'react-i18next';
import { LayoutDashboard, RefreshCw } from 'lucide-react';
import PageHeader from '../../shared/PageHeader';
import KpiStrip, { type Kpi } from './KpiStrip';
import OverviewCharts from './OverviewCharts';
import { useOverview } from './hooks';
import { OVERVIEW_STYLES } from './styles';

const OverviewTab = () => {
  const { t } = useTranslation();
  const { data, loading, error, reload } = useOverview();

  const kpis: Kpi[] = data
    ? [
        {
          key: 'users',
          label: t('overview.kpi.users'),
          value: data.totalUsers.toLocaleString(),
          sub: t('overview.kpi.usersHint', { active: data.activeUsers }),
        },
        {
          key: 'admins',
          label: t('overview.kpi.admins'),
          value: data.admins.toLocaleString(),
        },
        {
          key: 'sessions',
          label: t('overview.kpi.sessions'),
          value: data.activeSessions.toLocaleString(),
        },
        {
          key: 'failed',
          label: t('overview.kpi.failed'),
          value: data.failedLogins.toLocaleString(),
          dot: data.failedLogins ? 'warn' : 'ok',
        },
        {
          key: 'mfa',
          label: t('overview.kpi.mfa'),
          value: `${data.mfa.pct}%`,
          dot: data.mfa.pct >= 80 ? 'ok' : data.mfa.pct >= 50 ? 'warn' : 'bad',
        },
        ...(data.usage
          ? [
              {
                key: 'spend',
                label: t('overview.kpi.spend'),
                value: `$${data.usage.totalSpend.toFixed(2)}`,
              } as Kpi,
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
          <KpiStrip items={kpis} />
          <OverviewCharts data={data} />
          <section className="admin-card ov-card">
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
