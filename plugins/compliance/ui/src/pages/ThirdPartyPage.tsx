import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { api } from '../lib/api';
import { useApi } from '../lib/useApi';
import { useToast } from '../store/useToast';
import { Badge, Button, Card, Empty, ErrorNote, Field, Kpi, Skeleton } from '../components/ui';

export function ThirdPartyPage() {
  const { t } = useTranslation();
  const push = useToast((s) => s.push);
  const providers = useApi(() => api.tpProviders());
  const conc = useApi(() => api.tpConcentration());
  const [name, setName] = useState('');
  const [country, setCountry] = useState('');
  const [critical, setCritical] = useState(false);
  const [busy, setBusy] = useState(false);

  async function add() {
    if (!name.trim()) return;
    setBusy(true);
    try {
      await api.addProvider({ name, country: country || null, is_critical_designated: critical });
      setName('');
      setCountry('');
      setCritical(false);
      push(t('tp.added'));
      providers.reload();
      conc.reload();
    } catch (e) {
      push(e instanceof Error ? e.message : 'error', 'err');
    } finally {
      setBusy(false);
    }
  }

  async function exportRegister() {
    try {
      const data = await api.tpExport();
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'dora-register-of-information.json';
      a.click();
      URL.revokeObjectURL(url);
      push(t('tp.exported'));
    } catch (e) {
      push(e instanceof Error ? e.message : 'error', 'err');
    }
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>{t('tab.thirdparty')}</h1>
          <p>{t('tp.lead')}</p>
        </div>
        <div className="page-actions">
          <Button variant="ghost" onClick={exportRegister}>{t('tp.export')}</Button>
        </div>
      </div>

      <Card title={t('tp.concentration')}>
        {conc.error && <ErrorNote text={conc.error} />}
        {conc.loading && <Skeleton rows={1} />}
        {conc.data && (
          <div className="kpis">
            <Kpi icon="🏢" value={conc.data.providers} label={t('tp.k_providers')} />
            <Kpi icon="📄" value={conc.data.arrangements} label={t('tp.k_arrangements')} />
            <Kpi icon="★" value={conc.data.critical_or_important_arrangements} label={t('tp.k_critical')} />
            <Kpi icon="⚑" value={conc.data.concentration_flags.length} label={t('tp.k_flags')} alert={conc.data.concentration_flags.length > 0} />
          </div>
        )}
      </Card>

      <Card title={t('tp.add_provider')}>
        <div className="form-row">
          <Field label={t('field.name')}>
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder={t('tp.name_ph')} />
          </Field>
          <Field label={t('tp.country')}>
            <input value={country} onChange={(e) => setCountry(e.target.value)} placeholder="IT" />
          </Field>
          <label className="check">
            <input type="checkbox" checked={critical} onChange={(e) => setCritical(e.target.checked)} />
            {t('tp.critical_designated')}
          </label>
          <Button onClick={add} disabled={busy || !name.trim()}>{t('action.add')}</Button>
        </div>
      </Card>

      <Card title={t('tp.providers')}>
        {providers.error && <ErrorNote text={providers.error} />}
        {providers.loading ? (
          <Skeleton rows={3} />
        ) : providers.data && providers.data.providers.length === 0 ? (
          <Empty text={t('tp.no_providers')} />
        ) : (
          <table className="tbl">
            <thead>
              <tr>
                <th>{t('field.name')}</th>
                <th>{t('tp.country')}</th>
                <th>{t('tp.type')}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {providers.data?.providers.map((p) => (
                <tr key={p.id}>
                  <td className="t-main">{p.name}</td>
                  <td className="muted">{p.country ?? '—'}</td>
                  <td className="muted">{p.provider_type}</td>
                  <td>{p.is_critical_designated && <Badge tone="danger">{t('tp.critical')}</Badge>}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
