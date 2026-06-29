import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { api } from '../lib/api';
import { useApi } from '../lib/useApi';
import { useToast } from '../store/useToast';
import { Badge, Button, Card, Field, Skeleton } from '../components/ui';

export function TransparencyPage() {
  const { t } = useTranslation();
  const push = useToast((s) => s.push);
  const status = useApi(() => api.transparencyStatus());
  const [content, setContent] = useState('');
  const [model, setModel] = useState('');
  const [tag, setTag] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  async function mark() {
    if (!content.trim()) return;
    setBusy(true);
    try {
      const r = await api.mark({ content, model: model || null });
      setTag(r);
      push(t('tr.marked'));
    } catch (e) {
      push(e instanceof Error ? e.message : 'error', 'err');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page">
      <div className="page-head">
        <div>
          <h1>{t('tab.transparency')}</h1>
          <p>{t('tr.lead')}</p>
        </div>
      </div>

      <Card title={t('tr.status')}>
        {status.loading && <Skeleton rows={1} />}
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
        {tag != null && <pre className="json">{JSON.stringify(tag, null, 2)}</pre>}
      </Card>
    </div>
  );
}
