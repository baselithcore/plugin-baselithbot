import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { api } from '../lib/api';
import { useApi } from '../lib/useApi';
import { Badge, Button, Card, Empty, ErrorNote, Field } from '../components/ui';

export function DsrPage() {
  const { t } = useTranslation();
  const providers = useApi(() => api.dsrProviders());
  const [subject, setSubject] = useState('');
  const [result, setResult] = useState<unknown>(null);
  const [note, setNote] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  async function doExport() {
    if (!subject.trim()) return;
    setBusy('export');
    setNote(null);
    try {
      const r = await api.dsrExport(subject.trim());
      setResult(r);
    } catch (e) {
      setNote(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  }

  async function doErase() {
    if (!subject.trim()) return;
    if (!window.confirm(t('dsr.erase_confirm', { id: subject }))) return;
    setBusy('erase');
    setNote(null);
    try {
      const r = await api.dsrErase(subject.trim());
      setResult(r);
      setNote(t('dsr.erased', { count: r.total }));
    } catch (e) {
      setNote(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="page">
      <Card title={t('dsr.providers')}>
        {providers.error && <ErrorNote text={providers.error} />}
        {providers.loading && <Empty text={t('state.loading')} />}
        <div className="chips">
          {providers.data?.providers.map((p) => (
            <Badge key={p}>{p}</Badge>
          ))}
          {providers.data && providers.data.providers.length === 0 && <Empty text={t('dsr.no_providers')} />}
        </div>
      </Card>

      <Card title={t('dsr.request')}>
        <div className="form-row">
          <Field label={t('dsr.subject')}>
            <input value={subject} onChange={(e) => setSubject(e.target.value)} placeholder={t('dsr.subject_ph')} />
          </Field>
          <Button onClick={doExport} disabled={busy !== null || !subject.trim()}>{t('dsr.export')}</Button>
          <Button variant="danger" onClick={doErase} disabled={busy !== null || !subject.trim()}>{t('dsr.erase')}</Button>
        </div>
        {note && <p className="error-note">{note}</p>}
        {result != null && <pre className="json">{JSON.stringify(result, null, 2)}</pre>}
      </Card>
    </div>
  );
}
