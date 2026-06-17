// Audit trail: an immutable, newest-first log of every governance action — who
// approved/rejected a send, edited the whitelist, retrained the style, or
// toggled the kill-switch. The compliance backbone of the enterprise twin.

import { useTranslation } from 'react-i18next';
import { ShieldCheck, ShieldAlert } from 'lucide-react';
import type { AuditAction, AuditEvent } from '../api/types';
import { Badge, Card } from './ui';

const TONE: Record<string, 'good' | 'warn' | 'bad' | 'brand' | 'neutral'> = {
  'reply.approved': 'good',
  'reply.auto_sent': 'brand',
  'reply.rejected': 'warn',
  'reply.send_failed': 'bad',
  'webhook.rejected': 'bad',
  'twin.paused': 'warn',
  'twin.resumed': 'good',
};

function actionTone(action: AuditAction) {
  return TONE[action] ?? 'neutral';
}

export function AuditPanel({ events }: { events: AuditEvent[] }) {
  const { t } = useTranslation();
  return (
    <Card title={t('audit.title')}>
      {events.length === 0 ? (
        <p className="py-6 text-center text-sm text-white/30">{t('audit.empty')}</p>
      ) : (
        <ul className="max-h-72 space-y-2 overflow-y-auto pr-1">
          {events.map((e) => (
            <li
              key={e.id}
              className="flex items-start gap-2 rounded-xl border border-white/5 bg-white/[0.02] p-3"
            >
              {e.success ? (
                <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" aria-hidden />
              ) : (
                <ShieldAlert className="mt-0.5 h-4 w-4 shrink-0 text-rose-400" aria-hidden />
              )}
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-1.5">
                  <Badge tone={actionTone(e.action)}>{t(`audit.action.${e.action}`)}</Badge>
                  {e.resource && (
                    <span className="truncate font-mono text-[10px] text-white/40">
                      {e.resource}
                    </span>
                  )}
                </div>
                <p className="mt-1 text-xs text-white/50">
                  <span className="text-white/70">{e.actor}</span>
                  {' · '}
                  {new Date(e.at).toLocaleString()}
                  {e.ip_address ? ` · ${e.ip_address}` : ''}
                </p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
