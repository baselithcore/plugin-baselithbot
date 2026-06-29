import { useState } from 'react';
import { useTranslation } from 'react-i18next';

import { api } from '../lib/api';
import { useApi } from '../lib/useApi';
import { Badge, Button, Card, Empty, ErrorNote, Field } from '../components/ui';
import type { Incident } from '../types';

const STEPS = ['initial-notification', 'intermediate-report', 'final-report', 'close'];

export function DoraPage() {
  const { t } = useTranslation();
  const { data, error, loading, reload } = useApi(() => api.listDora());
  const [title, setTitle] = useState('');
  const [clients, setClients] = useState(0);
  const [busy, setBusy] = useState<string | null>(null);

  async function open() {
    if (!title.trim()) return;
    setBusy('open');
    try {
      await api.openDora({ title, affected_clients: clients });
      setTitle('');
      setClients(0);
      reload();
    } finally {
      setBusy(null);
    }
  }

  async function classifyMajor(inc: Incident) {
    setBusy(inc.id + 'cls');
    try {
      // Critical services + ≥2 other criteria ⇒ major (Delegated Reg. 2024/1772).
      await api.classifyDora(inc.id, {
        critical_services_affected: true,
        clients_affected: true,
        service_downtime: true,
      });
      reload();
    } finally {
      setBusy(null);
    }
  }

  async function advance(inc: Incident, step: string) {
    setBusy(inc.id + step);
    try {
      await api.advanceDora(inc.id, step);
      reload();
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="page">
      <Card
        title={t('dora.open')}
        action={data ? <Badge tone={data.overdue_count ? 'danger' : 'ok'}>{t('incidents.overdue', { count: data.overdue_count })}</Badge> : null}
      >
        <div className="form-row">
          <Field label={t('field.title')}>
            <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder={t('dora.title_ph')} />
          </Field>
          <Field label={t('dora.clients')}>
            <input type="number" min={0} value={clients} onChange={(e) => setClients(Number(e.target.value))} />
          </Field>
          <Button onClick={open} disabled={busy === 'open' || !title.trim()}>{t('action.record')}</Button>
        </div>
      </Card>

      {error && <ErrorNote text={error} />}
      {loading && <Empty text={t('state.loading')} />}
      {data && data.incidents.length === 0 && <Empty text={t('dora.none')} />}

      {data?.incidents.map((inc) => (
        <Card
          key={inc.id}
          title={inc.title}
          action={<Badge tone={inc.is_major ? 'danger' : 'neutral'}>{inc.is_major ? t('dora.major') : t('dora.not_major')}</Badge>}
        >
          <div className="meta-row">
            <Badge>{t(`status.${inc.status}`, inc.status)}</Badge>
            <span className="muted">{new Date(inc.detected_at).toLocaleString()}</span>
          </div>
          {inc.milestones.length === 0 ? (
            <div className="actions">
              <Button onClick={() => classifyMajor(inc)} disabled={busy === inc.id + 'cls'}>{t('dora.classify_major')}</Button>
            </div>
          ) : (
            <>
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
            </>
          )}
        </Card>
      ))}
    </div>
  );
}
