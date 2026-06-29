import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { api } from '../lib/api';
import { useApi } from '../lib/useApi';
import { useToast } from '../store/useToast';
import { Badge, Button, Card, Empty, ErrorNote, Field, Skeleton } from '../components/ui';

function download(name: string, payload: unknown) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

export function DsrPage() {
  const { t } = useTranslation();
  const push = useToast((s) => s.push);
  const providers = useApi(() => api.dsrProviders());
  const [subject, setSubject] = useState('');
  const [result, setResult] = useState<unknown>(null);
  const [busy, setBusy] = useState<string | null>(null);

  async function doExport() {
    if (!subject.trim()) return;
    setBusy('export');
    try {
      const r = await api.dsrExport(subject.trim());
      setResult(r);
      push(t('dsr.exported'));
    } catch (e) {
      push(e instanceof Error ? e.message : 'error', 'err');
    } finally {
      setBusy(null);
    }
  }

  async function doErase() {
    if (!subject.trim()) return;
    if (!window.confirm(t('dsr.erase_confirm', { id: subject }))) return;
    setBusy('erase');
    try {
      const r = await api.dsrErase(subject.trim());
      setResult(r);
      push(t('dsr.erased', { count: r.total }));
    } catch (e) {
      push(e instanceof Error ? e.message : 'error', 'err');
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>{t('tab.dsr')}</h1>
          <p>{t('dsr.lead')}</p>
        </div>
      </div>

      <Card title={t('dsr.providers')}>
        {providers.error && <ErrorNote text={providers.error} />}
        {providers.loading && <Skeleton rows={1} />}
        <div className="chips">
          {providers.data?.providers.map((p) => <Badge key={p} tone="accent">{p}</Badge>)}
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
        {result != null && (
          <>
            <div className="actions">
              <Button small variant="ghost" onClick={() => download(`dsr-${subject}.json`, result)}>{t('action.download')}</Button>
            </div>
            <pre className="json">{JSON.stringify(result, null, 2)}</pre>
          </>
        )}
      </Card>
    </div>
  );
}
