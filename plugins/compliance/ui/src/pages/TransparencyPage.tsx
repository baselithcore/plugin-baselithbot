import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { api } from '../lib/api';
import { useApi } from '../lib/useApi';
import { Badge, Button, Card, Empty, ErrorNote, Field } from '../components/ui';

export function TransparencyPage() {
  const { t } = useTranslation();
  const status = useApi(() => api.transparencyStatus());
  const [content, setContent] = useState('');
  const [model, setModel] = useState('');
  const [tag, setTag] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  async function mark() {
    if (!content.trim()) return;
    setBusy(true);
    setErr(null);
    try {
      const r = await api.mark({ content, model: model || null });
      setTag(r);
    } catch (e) {
      setErr(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <Card title={t('tr.status')}>
        {status.error && <ErrorNote text={status.error} />}
        {status.loading && <Empty text={t('state.loading')} />}
        {status.data && (
          <div className="meta-row">
            <Badge tone={status.data.enabled ? 'ok' : 'neutral'}>
              {status.data.enabled ? t('tr.enabled') : t('tr.disabled')}
            </Badge>
            <Badge tone={status.data.should_disclose ? 'warn' : 'neutral'}>
              {t('tr.should_disclose')}: {status.data.should_disclose ? t('common.yes') : t('common.no')}
            </Badge>
          </div>
        )}
        {status.data?.notice && <pre className="json">{JSON.stringify(status.data.notice, null, 2)}</pre>}
      </Card>

      <Card title={t('tr.mark')}>
        <div className="form-col">
          <Field label={t('tr.content')}>
            <textarea value={content} onChange={(e) => setContent(e.target.value)} rows={3} placeholder={t('tr.content_ph')} />
          </Field>
          <div className="form-row">
            <Field label={t('tr.model')}>
              <input value={model} onChange={(e) => setModel(e.target.value)} placeholder="claude-opus-4-8" />
            </Field>
            <Button onClick={mark} disabled={busy || !content.trim()}>{t('tr.generate')}</Button>
          </div>
        </div>
        {err && <p className="error-note">{err}</p>}
        {tag != null && <pre className="json">{JSON.stringify(tag, null, 2)}</pre>}
      </Card>
    </div>
  );
}
