import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';

import { api } from '../lib/api';
import { useApi } from '../lib/useApi';
import { useToast } from '../store/useToast';
import { Badge, Button, Card, Empty, ErrorNote, Field, Skeleton } from '../components/ui';
import { DeadlineMeter } from '../components/DeadlineMeter';
import { Drawer } from '../components/Drawer';
import { dateTime } from '../lib/format';
import type { Incident } from '../types';

const SEVERITIES = ['low', 'medium', 'high', 'critical'];
const STEPS = ['early-warning', 'notification', 'final-report', 'close'];

function sevTone(s: string): 'neutral' | 'warn' | 'danger' {
  return s === 'critical' || s === 'high' ? 'danger' : s === 'medium' ? 'warn' : 'neutral';
}

export function IncidentsPage() {
  const { t } = useTranslation();
  const push = useToast((s) => s.push);
  const { data, error, loading, reload } = useApi(() => api.listIncidents());
  const [title, setTitle] = useState('');
  const [severity, setSeverity] = useState('medium');
  const [filter, setFilter] = useState('all');
  const [openId, setOpenId] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const rows = useMemo(
    () => (data?.incidents ?? []).filter((i) => filter === 'all' || i.status === filter),
    [data, filter]
  );
  const selected = data?.incidents.find((i) => i.id === openId) ?? null;

  async function open() {
    if (!title.trim()) return;
    setBusy('open');
    try {
      await api.openIncident({ title, severity, significant: true });
      setTitle('');
      push(t('incidents.created'));
      reload();
    } catch (e) {
      push(e instanceof Error ? e.message : 'error', 'err');
    } finally {
      setBusy(null);
    }
  }

  async function advance(inc: Incident, step: string) {
    setBusy(inc.id + step);
    try {
      await api.advanceIncident(inc.id, step);
      push(t('step.done', { step: t(`step.${step}`) }));
      reload();
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
          <h1>{t('tab.incidents')}</h1>
          <p>{t('incidents.lead')}</p>
        </div>
        {data && (
          <Badge tone={data.overdue_count ? 'danger' : 'ok'}>
            {t('incidents.overdue', { count: data.overdue_count })}
          </Badge>
        )}
      </div>

      <Card title={t('incidents.open')}>
        <div className="form-row">
          <Field label={t('field.title')}>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder={t('incidents.title_ph')}
            />
          </Field>
          <Field label={t('field.severity')}>
            <select value={severity} onChange={(e) => setSeverity(e.target.value)}>
              {SEVERITIES.map((s) => (
                <option key={s} value={s}>
                  {t(`severity.${s}`)}
                </option>
              ))}
            </select>
          </Field>
          <Button onClick={open} disabled={busy === 'open' || !title.trim()}>
            {t('action.record')}
          </Button>
        </div>
      </Card>

      {error && <ErrorNote text={error} />}
      <Card
        title={t('incidents.registry')}
        action={
          <div className="filter-bar">
            <select value={filter} onChange={(e) => setFilter(e.target.value)}>
              <option value="all">{t('filter.all')}</option>
              {[
                'detected',
                'early_warning_submitted',
                'notification_submitted',
                'final_submitted',
                'closed',
              ].map((s) => (
                <option key={s} value={s}>
                  {t(`status.${s}`)}
                </option>
              ))}
            </select>
          </div>
        }
      >
        {loading ? (
          <Skeleton rows={4} />
        ) : rows.length === 0 ? (
          <Empty text={t('incidents.none')} />
        ) : (
          <table className="tbl">
            <thead>
              <tr>
                <th>{t('field.title')}</th>
                <th>{t('field.severity')}</th>
                <th>{t('col.status')}</th>
                <th>{t('col.detected')}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((inc) => (
                <tr key={inc.id} className="clickable" onClick={() => setOpenId(inc.id)}>
                  <td className="t-main">{inc.title}</td>
                  <td>
                    <Badge tone={sevTone(inc.severity)}>{t(`severity.${inc.severity}`)}</Badge>
                  </td>
                  <td>
                    <Badge>{t(`status.${inc.status}`, inc.status)}</Badge>
                  </td>
                  <td className="muted">{dateTime(inc.detected_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {selected && (
        <Drawer title={selected.title} onClose={() => setOpenId(null)}>
          <div className="meta-row">
            <Badge tone={sevTone(selected.severity)}>{t(`severity.${selected.severity}`)}</Badge>
            <Badge>{t(`status.${selected.status}`, selected.status)}</Badge>
          </div>
          {selected.description && <p className="desc">{selected.description}</p>}
          <div className="form-col">
            {selected.milestones.map((m) => (
              <DeadlineMeter
                key={m.kind}
                kind={m.kind}
                dueAt={m.due_at}
                label={t(`milestone.${m.kind}`, m.kind)}
              />
            ))}
          </div>
          <div className="actions">
            {STEPS.map((s) => (
              <Button
                key={s}
                small
                variant={s === 'close' ? 'danger' : 'ghost'}
                onClick={() => advance(selected, s)}
                disabled={busy === selected.id + s}
              >
                {t(`step.${s}`)}
              </Button>
            ))}
          </div>
        </Drawer>
      )}
    </div>
  );
}
