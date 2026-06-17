// Human-in-the-loop approval queue. Shows each queued reply with the inbound
// message and the twin's draft, and lets the operator approve (send) or reject.

import { useTranslation } from 'react-i18next';
import { Check, X } from 'lucide-react';
import type { PendingReply } from '../api/types';
import { Badge, Button, Card } from './ui';

export function ApprovalQueue({
  queue,
  onDecide,
}: {
  queue: PendingReply[];
  onDecide: (id: string, approve: boolean) => void;
}) {
  const { t } = useTranslation();
  const pending = queue.filter((r) => r.status === 'queued');
  return (
    <Card title={`${t('queue.title')} (${pending.length})`}>
      {pending.length === 0 ? (
        <p className="py-8 text-center text-sm text-white/30">{t('queue.empty')}</p>
      ) : (
        <ul className="space-y-3">
          {pending.map((r) => (
            <li key={r.id} className="rounded-xl border border-white/5 bg-white/[0.02] p-4">
              <div className="mb-2 flex items-center justify-between">
                <span className="font-mono text-xs text-white/50">
                  {t('queue.from')}: {r.contact_id}
                </span>
                <div className="flex items-center gap-2">
                  {r.draft.degraded && <Badge tone="warn">{t('queue.degraded')}</Badge>}
                  <Badge tone="brand">
                    {t('queue.confidence')} {(r.draft.confidence * 100).toFixed(0)}%
                  </Badge>
                </div>
              </div>
              <p className="text-xs text-white/40">{t('queue.inbound')}:</p>
              <p className="mb-2 text-sm text-white/70">{r.inbound_text}</p>
              <p className="text-xs text-white/40">{t('queue.draft')}:</p>
              <p className="mb-3 rounded-lg bg-brand-500/5 p-2 text-sm text-white/90">
                {r.draft.text}
              </p>
              <div className="flex gap-2">
                <Button variant="primary" onClick={() => onDecide(r.id, true)}>
                  <Check className="mr-1 inline h-3.5 w-3.5" />
                  {t('queue.approve')}
                </Button>
                <Button variant="danger" onClick={() => onDecide(r.id, false)}>
                  <X className="mr-1 inline h-3.5 w-3.5" />
                  {t('queue.reject')}
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
