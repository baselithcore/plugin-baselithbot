import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { api } from '../lib/api';
import { useApi } from '../lib/useApi';
import { Badge, Button, Card, Empty, ErrorNote, Field } from '../components/ui';

export function ThirdPartyPage() {
  const { t } = useTranslation();
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
      providers.reload();
      conc.reload();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <Card title={t('tp.concentration')}>
        {conc.error && <ErrorNote text={conc.error} />}
        {conc.data && (
          <div className="kpis">
            <div className="kpi"><strong>{conc.data.providers}</strong><span>{t('tp.k_providers')}</span></div>
            <div className="kpi"><strong>{conc.data.arrangements}</strong><span>{t('tp.k_arrangements')}</span></div>
            <div className="kpi"><strong>{conc.data.critical_or_important_arrangements}</strong><span>{t('tp.k_critical')}</span></div>
            <div className="kpi"><strong>{conc.data.concentration_flags.length}</strong><span>{t('tp.k_flags')}</span></div>
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
        {providers.loading && <Empty text={t('state.loading')} />}
        {providers.data && providers.data.providers.length === 0 && <Empty text={t('tp.no_providers')} />}
        <ul className="rows">
          {providers.data?.providers.map((p) => (
            <li key={p.id} className="row">
              <span className="row-main">{p.name}</span>
              <span className="muted">{p.country ?? '—'}</span>
              {p.is_critical_designated && <Badge tone="danger">{t('tp.critical')}</Badge>}
            </li>
          ))}
        </ul>
      </Card>
    </div>
  );
}
