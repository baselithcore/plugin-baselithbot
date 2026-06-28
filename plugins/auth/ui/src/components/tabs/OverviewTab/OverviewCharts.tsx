/** Chart cards for the Overview dashboard: activity, MFA, roles, AI usage. */

import { useTranslation } from 'react-i18next';
import { AreaChart, BarList, Donut } from './charts';
import type { OverviewData } from './hooks';

const fmtUsd = (v: number): string => `$${v < 1 ? v.toFixed(3) : v.toFixed(2)}`;

const OverviewCharts = ({ data }: { data: OverviewData }) => {
  const { t } = useTranslation();
  const activityTotal = data.activity.values.reduce((a, b) => a + b, 0);
  const lastLabel = data.activity.labels[data.activity.labels.length - 1];

  return (
    <div className="ov-grid">
      <section className="admin-card ov-card ov-card-wide">
        <header className="ov-card-head">
          <h3>{t('overview.activity.title')}</h3>
          <span className="ov-card-sub">{t('overview.activity.sub', { count: activityTotal })}</span>
        </header>
        <AreaChart values={data.activity.values} />
        <div className="ov-axis">
          <span>{data.activity.labels[0]}</span>
          <span>{lastLabel}</span>
        </div>
      </section>

      <section className="admin-card ov-card">
        <header className="ov-card-head">
          <h3>{t('overview.mfa.title')}</h3>
        </header>
        <Donut pct={data.mfa.pct} center={`${data.mfa.pct}%`} caption={t('overview.mfa.caption')} />
        <p className="ov-card-foot">
          {t('overview.mfa.detail', { enabled: data.mfa.enabled, total: data.mfa.total })}
        </p>
      </section>

      <section className="admin-card ov-card">
        <header className="ov-card-head">
          <h3>{t('overview.roles.title')}</h3>
        </header>
        {data.roles.length ? (
          <BarList items={data.roles.map((r) => ({ label: r.role, value: r.count }))} />
        ) : (
          <p className="ov-empty">{t('overview.empty')}</p>
        )}
      </section>

      {data.usage && (
        <section className="admin-card ov-card ov-card-wide">
          <header className="ov-card-head">
            <h3>{t('overview.usage.title')}</h3>
            <span className="ov-card-sub">
              {t('overview.usage.sub', {
                spend: fmtUsd(data.usage.totalSpend),
                reqs: data.usage.totalRequests,
              })}
            </span>
          </header>
          {data.usage.top.length ? (
            <BarList items={data.usage.top} format={fmtUsd} />
          ) : (
            <p className="ov-empty">{t('overview.usage.empty')}</p>
          )}
        </section>
      )}
    </div>
  );
};

export default OverviewCharts;
