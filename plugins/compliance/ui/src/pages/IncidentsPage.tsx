import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { api } from '../lib/api';
import { useApi } from '../lib/useApi';
import { Badge, Button, Card, Empty, ErrorNote, Field } from '../components/ui';
import type { Incident } from '../types';

const SEVERITIES = ['low', 'medium', 'high', 'critical'];
const STEPS = ['early-warning', 'notification', 'final-report', 'close'];

function severityTone(s: string): 'neutral' | 'warn' | 'danger' {
  if (s === 'critical' || s === 'high') return 'danger';
  if (s === 'medium') return 'warn';
  return 'neutral';
}

export function IncidentsPage() {
  const { t } = useTranslation();
  const { data, error, loading, reload } = useApi(() => api.listIncidents());
  const [title, setTitle] = useState('');
  const [severity, setSeverity] = useState('medium');
  const [busy, setBusy] = useState<string | null>(null);

  async function open() {
    if (!title.trim()) return;
    setBusy('open');
    try {
      await api.openIncident({ title, severity, significant: true });
      setTitle('');
      reload();
    } finally {
      setBusy(null);
    }
  }

  async function advance(inc: Incident, step: string) {
    setBusy(inc.id + step);
    try {
      await api.advanceIncident(inc.id, step);
      reload();
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="page">
      <Card
        title={t('incidents.open')}
        action={
          data ? <Badge tone={data.overdue_count ? 'danger' : 'ok'}>{t('incidents.overdue', { count: data.overdue_count })}</Badge> : null
        }
      >
        <div className="form-row">
          <Field label={t('field.title')}>
            <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder={t('incidents.title_ph')} />
          </Field>
          <Field label={t('field.severity')}>
            <select value={severity} onChange={(e) => setSeverity(e.target.value)}>
              {SEVERITIES.map((s) => (
                <option key={s} value={s}>{t(`severity.${s}`)}</option>
              ))}
            </select>
          </Field>
          <Button onClick={open} disabled={busy === 'open' || !title.trim()}>{t('action.record')}</Button>
        </div>
      </Card>

      {error && <ErrorNote text={error} />}
      {loading && <Empty text={t('state.loading')} />}
      {data && data.incidents.length === 0 && <Empty text={t('incidents.none')} />}

      {data?.incidents.map((inc) => (
        <Card key={inc.id} title={inc.title} action={<Badge tone={severityTone(inc.severity)}>{t(`severity.${inc.severity}`)}</Badge>}>
          <div className="meta-row">
            <Badge>{t(`status.${inc.status}`, inc.status)}</Badge>
            <span className="muted">{new Date(inc.detected_at).toLocaleString()}</span>
          </div>
          {inc.description && <p className="desc">{inc.description}</p>}
          <ul className="milestones">
            {inc.milestones.map((m) => (
              <li key={m.kind}>
                <span>{t(`milestone.${m.kind}`, m.kind)}</span>
                <Badge tone={m.submitted ? 'ok' : m.overdue ? 'danger' : 'warn'}>
                  {m.submitted ? t('ms.done') : m.overdue ? t('ms.overdue') : new Date(m.due_at).toLocaleString()}
                </Badge>
              </li>
            ))}
          </ul>
          <div className="actions">
            {STEPS.map((s) => (
              <Button key={s} variant={s === 'close' ? 'danger' : 'ghost'} onClick={() => advance(inc, s)} disabled={busy === inc.id + s}>
                {t(`step.${s}`)}
              </Button>
            ))}
          </div>
        </Card>
      ))}
    </div>
  );
}
