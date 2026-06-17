import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Check, X, Clock, ScrollText, Gavel } from 'lucide-react';
import { api } from '../api';
import type { AckStatus, AuditRecord, Recommendation, RecommendationAck } from '../types';
import { Panel, Badge } from './ui';

interface Props {
  recs: Recommendation[];
  sessionId: string;
}

const ACK_TONE: Record<AckStatus, 'go' | 'danger' | 'caution'> = {
  accepted: 'go',
  rejected: 'danger',
  deferred: 'caution',
};
const ACK_KEY: Record<AckStatus, string> = {
  accepted: 'accept',
  rejected: 'reject',
  deferred: 'defer',
};

// HITL accept/reject/defer over recent recommendations + the immutable audit ledger.
export function GovernancePanel({ recs, sessionId }: Props) {
  const { t } = useTranslation();
  const [audit, setAudit] = useState<AuditRecord[]>([]);
  const [acks, setAcks] = useState<Record<string, AckStatus>>({});

  const refresh = useCallback(async () => {
    try {
      const [a, ks] = await Promise.all([api.audit(40), api.acks()]);
      setAudit(a);
      setAcks(
        ks.reduce<Record<string, AckStatus>>((m, k: RecommendationAck) => {
          m[k.recommendation_id] = k.status;
          return m;
        }, {})
      );
    } catch {
      /* warming up or unauthorized */
    }
  }, []);

  useEffect(() => {
    void refresh();
    const id = setInterval(refresh, 4000);
    return () => clearInterval(id);
  }, [refresh, sessionId]);

  const ack = useCallback(
    async (recId: string, status: AckStatus) => {
      setAcks((prev) => ({ ...prev, [recId]: status }));
      await api.acknowledge(recId, status).catch(() => undefined);
      await refresh();
    },
    [refresh]
  );

  const btn =
    'grid h-8 w-8 place-items-center rounded-lg border border-hair bg-surface-2 transition hover:border-hair-strong';

  return (
    <div className="space-y-4">
      <Panel title={t('history')} eyebrow={t('hitl')} icon={<Gavel size={16} />} tone="ember">
        {recs.length === 0 ? (
          <p className="py-3 text-center text-sm text-faint">{t('empty')}</p>
        ) : (
          <ul className="space-y-2">
            {recs.slice(0, 10).map((r) => (
              <li
                key={r.id}
                className="flex items-center justify-between gap-2 rounded-xl border border-hair bg-surface-2/60 px-3 py-2"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm text-ink">
                    <span className="tabular text-dim">{r.car_id}</span> · {t(`kind_${r.kind}`)}
                  </p>
                  <p className="tabular text-[11px] text-faint">
                    {t('lap')} {r.lap} · {Math.round(r.confidence * 100)}%
                  </p>
                </div>
                {acks[r.id] ? (
                  <Badge tone={ACK_TONE[acks[r.id]]}>{t(ACK_KEY[acks[r.id]])}</Badge>
                ) : (
                  <div className="flex shrink-0 items-center gap-1">
                    <button
                      onClick={() => void ack(r.id, 'accepted')}
                      title={t('accept')}
                      className={`${btn} text-go`}
                    >
                      <Check size={13} />
                    </button>
                    <button
                      onClick={() => void ack(r.id, 'rejected')}
                      title={t('reject')}
                      className={`${btn} text-danger`}
                    >
                      <X size={13} />
                    </button>
                    <button
                      onClick={() => void ack(r.id, 'deferred')}
                      title={t('defer')}
                      className={`${btn} text-caution`}
                    >
                      <Clock size={13} />
                    </button>
                  </div>
                )}
              </li>
            ))}
          </ul>
        )}
      </Panel>

      <Panel title={t('auditLog')} eyebrow={t('ledger')} icon={<ScrollText size={16} />}>
        {audit.length === 0 ? (
          <p className="py-3 text-center text-xs text-faint">{t('noAudit')}</p>
        ) : (
          <ul className="scroll-slim max-h-72 space-y-1.5 overflow-y-auto">
            {audit.map((a) => (
              <li
                key={a.id}
                className="flex items-center justify-between gap-2 border-b border-hair/60 pb-1.5 text-xs last:border-0"
              >
                <span className="truncate text-dim">{a.action}</span>
                <span className="tabular shrink-0 text-faint">{a.actor}</span>
              </li>
            ))}
          </ul>
        )}
      </Panel>
    </div>
  );
}
