import { useTranslation } from 'react-i18next';

import { api } from '../lib/api';
import { useApi } from '../lib/useApi';
import { Badge, Card, Empty, ErrorNote, Kpi, Skeleton } from '../components/ui';
import { DeadlineMeter } from '../components/DeadlineMeter';

export function OverviewPage() {
  const { t } = useTranslation();
  const { data, error, loading } = useApi(() => api.overview());

  const openIncidents = (data?.nis2.open ?? 0) + (data?.dora.open ?? 0);
  const overdue = (data?.nis2.overdue ?? 0) + (data?.dora.overdue ?? 0);

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>{t('ov.title')}</h1>
          <p>{t('ov.subtitle')}</p>
        </div>
      </div>

      {error && <ErrorNote text={error} />}
      {loading && (
        <Card>
          <Skeleton rows={4} />
        </Card>
      )}

      {data && (
        <>
          <div className="kpis">
            <Kpi icon="▲" value={openIncidents} label={t('ov.k_open')} />
            <Kpi icon="⏰" value={overdue} label={t('ov.k_overdue')} alert={overdue > 0} />
            <Kpi icon="⚡" value={data.dora.major} label={t('ov.k_major')} />
            <Kpi icon="⚲" value={data.dsr.providers} label={t('ov.k_providers')} />
            <Kpi icon="⛓" value={data.thirdparty.flags} label={t('ov.k_flags')} alert={data.thirdparty.flags > 0} />
            <Kpi
              icon="✦"
              value={data.transparency.enabled ? t('tr.enabled') : t('tr.disabled')}
              label={t('ov.k_disclosure')}
            />
          </div>

          <Card title={t('ov.deadlines')}>
            {data.deadlines.length === 0 ? (
              <Empty text={t('ov.no_deadlines')} />
            ) : (
              <div className="rows">
                {data.deadlines.map((d) => (
                  <div className="row" key={`${d.regime}-${d.incident_id}-${d.kind}`}>
                    <Badge tone={d.regime === 'dora' ? 'accent' : 'neutral'}>{d.regime.toUpperCase()}</Badge>
                    <span className="row-main">{d.title}</span>
                    <DeadlineMeter kind={d.kind} dueAt={d.due_at} label={t(`milestone.${d.kind}`, d.kind)} />
                  </div>
                ))}
              </div>
            )}
          </Card>

          <Card title={t('ov.concentration')}>
            <div className="kpis">
              <Kpi icon="🏢" value={data.thirdparty.providers} label={t('tp.k_providers')} />
              <Kpi icon="📄" value={data.thirdparty.arrangements} label={t('tp.k_arrangements')} />
              <Kpi icon="★" value={data.thirdparty.critical} label={t('tp.k_critical')} />
            </div>
          </Card>
        </>
      )}
    </div>
  );
}
