/** Analytical panels for the Overview console: activity, posture, role + AI usage. */

import { useTranslation } from 'react-i18next';
import { AreaChart, Meter } from './charts';
import Posture from './Posture';
import Governance from './Governance';
import type { OverviewData } from './hooks';

const fmtUsd = (v: number): string => `$${v < 1 ? v.toFixed(3) : v.toFixed(2)}`;

const OverviewCharts = ({ data }: { data: OverviewData }) => {
  const { t } = useTranslation();
  const activityTotal = data.activity.values.reduce((a, b) => a + b, 0);
  const roleTotal = data.roles.reduce((s, r) => s + r.count, 0) || 1;
  const usageMax = Math.max(0.0001, ...(data.usage?.top.map((u) => u.value) ?? []));

  return (
    <div className="ov-grid">
      <section className="admin-card ov-card ov-card-wide">
        <header className="ov-card-head">
          <h3>{t('overview.activity.title')}</h3>
          <span className="ov-card-sub">
            {t('overview.activity.sub', { count: activityTotal })}
          </span>
        </header>
        <AreaChart values={data.activity.values} />
        <div className="ov-axis">
          <span>{data.activity.labels[0]}</span>
          <span>{data.activity.labels[data.activity.labels.length - 1]}</span>
        </div>
      </section>

      <Posture data={data} />

      <Governance data={data} />

      <section className="admin-card ov-card">
        <header className="ov-card-head">
          <h3>{t('overview.roles.title')}</h3>
        </header>
        {data.roles.length ? (
          <div className="ov-rows">
            {data.roles.map((r) => {
              const share = Math.round((r.count / roleTotal) * 100);
              return (
                <div className="ov-row" key={r.role}>
                  <span className="ov-row-name mono">{r.role}</span>
                  <span className="ov-row-meter">
                    <Meter pct={share} />
                  </span>
                  <span className="ov-row-val">{r.count}</span>
                  <span className="ov-row-pct">{share}%</span>
                </div>
              );
            })}
          </div>
        ) : (
          <p className="ov-empty">{t('overview.empty')}</p>
        )}
      </section>

      {data.usage && (
        <section className="admin-card ov-card">
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
            <div className="ov-rows">
              {data.usage.top.map((u) => (
                <div className="ov-row ov-row-usage" key={u.label}>
                  <span className="ov-row-name" title={u.label}>
                    {u.label}
                  </span>
                  <span className="ov-row-meter">
                    <Meter pct={(u.value / usageMax) * 100} />
                  </span>
                  <span className="ov-row-val">{fmtUsd(u.value)}</span>
                </div>
              ))}
            </div>
          ) : (
            <p className="ov-empty">{t('overview.usage.empty')}</p>
          )}
        </section>
      )}
    </div>
  );
};

export default OverviewCharts;
