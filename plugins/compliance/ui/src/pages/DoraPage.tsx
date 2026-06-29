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

const STEPS = ['initial-notification', 'intermediate-report', 'final-report', 'close'];

export function DoraPage() {
  const { t } = useTranslation();
  const push = useToast((s) => s.push);
  const { data, error, loading, reload } = useApi(() => api.listDora());
  const [title, setTitle] = useState('');
  const [clients, setClients] = useState(0);
  const [filter, setFilter] = useState('all');
  const [openId, setOpenId] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  const rows = useMemo(
    () => (data?.incidents ?? []).filter((i) => filter === 'all' || i.status === filter),
    [data, filter],
  );
  const sel = data?.incidents.find((i) => i.id === openId) ?? null;

  async function open() {
    if (!title.trim()) return;
    setBusy('open');
    try {
      await api.openDora({ title, affected_clients: clients });
      setTitle('');
      setClients(0);
      push(t('dora.created'));
      reload();
    } catch (e) {
      push(e instanceof Error ? e.message : 'error', 'err');
    } finally {
      setBusy(null);
    }
  }

  async function classify(inc: Incident) {
    setBusy(inc.id + 'cls');
    try {
      await api.classifyDora(inc.id, {
        critical_services_affected: true,
        clients_affected: true,
        service_downtime: true,
      });
      push(t('dora.classified'));
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
      await api.advanceDora(inc.id, step);
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
          <h1>{t('tab.dora')}</h1>
          <p>{t('dora.lead')}</p>
        </div>
        {data && <Badge tone={data.overdue_count ? 'danger' : 'ok'}>{t('incidents.overdue', { count: data.overdue_count })}</Badge>}
      </div>

      <Card title={t('dora.open')}>
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
      <Card
        title={t('dora.registry')}
        action={
          <div className="filter-bar">
            <select value={filter} onChange={(e) => setFilter(e.target.value)}>
              <option value="all">{t('filter.all')}</option>
              {['detected', 'classified', 'initial_submitted', 'intermediate_submitted', 'final_submitted', 'closed'].map((s) => (
                <option key={s} value={s}>{t(`status.${s}`)}</option>
              ))}
            </select>
          </div>
        }
      >
        {loading ? (
          <Skeleton rows={4} />
        ) : rows.length === 0 ? (
          <Empty text={t('dora.none')} />
        ) : (
          <table className="tbl">
            <thead>
              <tr>
                <th>{t('field.title')}</th>
                <th>{t('dora.classification')}</th>
                <th>{t('col.status')}</th>
                <th>{t('col.detected')}</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((inc) => (
                <tr key={inc.id} className="clickable" onClick={() => setOpenId(inc.id)}>
                  <td className="t-main">{inc.title}</td>
                  <td><Badge tone={inc.is_major ? 'danger' : 'neutral'}>{inc.is_major ? t('dora.major') : t('dora.not_major')}</Badge></td>
                  <td><Badge>{t(`status.${inc.status}`, inc.status)}</Badge></td>
                  <td className="muted">{dateTime(inc.detected_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>

      {sel && (
        <Drawer title={sel.title} onClose={() => setOpenId(null)}>
          <div className="meta-row">
            <Badge tone={sel.is_major ? 'danger' : 'neutral'}>{sel.is_major ? t('dora.major') : t('dora.not_major')}</Badge>
            <Badge>{t(`status.${sel.status}`, sel.status)}</Badge>
          </div>
          {sel.milestones.length === 0 ? (
            <div className="actions">
              <Button onClick={() => classify(sel)} disabled={busy === sel.id + 'cls'}>{t('dora.classify_major')}</Button>
            </div>
          ) : (
            <>
              <div className="form-col">
                {sel.milestones.map((m) => (
                  <DeadlineMeter key={m.kind} kind={m.kind} dueAt={m.due_at} label={t(`milestone.${m.kind}`, m.kind)} />
                ))}
              </div>
              <div className="actions">
                {STEPS.map((s) => (
                  <Button key={s} small variant={s === 'close' ? 'danger' : 'ghost'} onClick={() => advance(sel, s)} disabled={busy === sel.id + s}>
                    {t(`step.${s}`)}
                  </Button>
                ))}
              </div>
            </>
          )}
        </Drawer>
      )}
    </div>
  );
}
