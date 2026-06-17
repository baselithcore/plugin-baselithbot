// Live activity stream rendered from the SSE channel. Each event type maps to a
// colour-coded badge so an operator can scan the twin's real-time behaviour.

import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'motion/react';
import type { StreamEvent } from '../api/types';
import { Badge, Card } from './ui';

const TONE: Record<string, 'neutral' | 'good' | 'warn' | 'brand'> = {
  inbound: 'neutral',
  draft: 'brand',
  queued: 'warn',
  auto_sent: 'good',
  decided: 'good',
  style_trained: 'brand',
};

function summarize(event: StreamEvent): string {
  const p = event.payload as Record<string, unknown>;
  if (event.type === 'inbound') return String(p.text ?? '');
  if (event.type === 'draft') return String(p.text ?? '');
  const draft = p.draft as Record<string, unknown> | undefined;
  if (draft) return String(draft.text ?? '');
  return '';
}

export function LiveFeed({ events }: { events: StreamEvent[] }) {
  const { t } = useTranslation();
  return (
    <Card title={t('feed.title')} className="h-full">
      {events.length === 0 ? (
        <p className="py-8 text-center text-sm text-white/30">{t('feed.empty')}</p>
      ) : (
        <ul className="max-h-[28rem] space-y-2 overflow-y-auto pr-1">
          <AnimatePresence initial={false}>
            {events.map((e, i) => (
              <motion.li
                key={`${e.at}-${i}`}
                initial={{ opacity: 0, y: -8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                className="rounded-xl border border-white/5 bg-white/[0.02] p-3"
              >
                <div className="flex items-center justify-between">
                  <Badge tone={TONE[e.type] ?? 'neutral'}>
                    {t(`feed.event.${e.type}`, e.type)}
                  </Badge>
                  <time className="text-[10px] text-white/30">
                    {new Date(e.at).toLocaleTimeString()}
                  </time>
                </div>
                {summarize(e) && (
                  <p className="mt-1.5 line-clamp-2 text-sm text-white/70">{summarize(e)}</p>
                )}
              </motion.li>
            ))}
          </AnimatePresence>
        </ul>
      )}
    </Card>
  );
}
