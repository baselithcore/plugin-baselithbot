import { useTranslation } from 'react-i18next';
import { motion, AnimatePresence } from 'motion/react';
import { CheckCircle2, ShieldAlert, Radio } from 'lucide-react';
import type { Recommendation } from '../types';
import { kindTone } from '../lib/race';
import { Ring } from './ui';

const ACCENT: Record<string, string> = {
  danger: 'bg-danger',
  caution: 'bg-caution',
  ember: 'bg-ember',
  go: 'bg-go',
  info: 'bg-info',
  neutral: 'bg-hair-strong',
};
const RING: Record<string, 'ember' | 'info' | 'go' | 'caution' | 'danger'> = {
  danger: 'danger',
  caution: 'caution',
  ember: 'ember',
  go: 'go',
  info: 'info',
  neutral: 'info',
};

function Card({ r }: { r: Recommendation }) {
  const { t } = useTranslation();
  const tone = kindTone(r.kind);
  const urgent = tone === 'danger' || !r.fia_verdict.compliant;
  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: -10, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, x: 12 }}
      transition={{ type: 'spring', stiffness: 380, damping: 30 }}
      className={`relative overflow-hidden rounded-xl border border-hair bg-surface-2/70 p-3 pl-4 ${
        urgent ? 'flash-glow' : ''
      }`}
    >
      <span className={`absolute inset-y-0 left-0 w-1 ${ACCENT[tone]}`} />
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="mb-0.5 flex items-center gap-2">
            <span className="font-display text-sm font-semibold text-ink">
              {t(`kind_${r.kind}`)}
            </span>
            <span className="tabular text-[11px] text-faint">{r.car_id}</span>
          </div>
          <p className="text-sm leading-snug text-ink/90">{r.summary}</p>
          {r.rationale && (
            <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-faint">{r.rationale}</p>
          )}
        </div>
        <Ring value={r.confidence} tone={RING[tone]} size={40} />
      </div>
      <div className="mt-2 flex items-center justify-between border-t border-hair pt-2">
        <span className="tabular text-[11px] text-dim">
          {t('lap')} {r.lap} · {t('confidence')} {(r.confidence * 100).toFixed(0)}%
        </span>
        <span
          className={`flex items-center gap-1 text-[11px] font-medium ${
            r.fia_verdict.compliant ? 'text-go' : 'text-danger'
          }`}
        >
          {r.fia_verdict.compliant ? <CheckCircle2 size={12} /> : <ShieldAlert size={12} />}
          {r.fia_verdict.compliant ? t('compliant') : t('violation')}
        </span>
      </div>
    </motion.article>
  );
}

export function RecommendationFeed({ recs }: { recs: Recommendation[] }) {
  const { t } = useTranslation();
  return (
    <section className="glass flex h-full flex-col overflow-hidden rounded-2xl">
      <header className="flex items-center justify-between border-b border-hair px-4 py-3">
        <div className="flex items-center gap-2">
          <Radio size={16} className="text-ember" />
          <div>
            <div className="eyebrow leading-none">{t('liveFeed')}</div>
            <h3 className="font-display text-sm font-semibold text-ink">{t('feed')}</h3>
          </div>
        </div>
        <span className="tabular rounded-full border border-hair bg-surface-2 px-2 py-0.5 text-[11px] text-dim">
          {recs.length}
        </span>
      </header>
      <div className="scroll-slim flex-1 space-y-2.5 overflow-y-auto p-3">
        {recs.length === 0 ? (
          <div className="grid h-full place-items-center py-12 text-center">
            <div>
              <Radio size={22} className="mx-auto mb-2 text-faint" />
              <p className="text-sm text-faint">{t('empty')}</p>
            </div>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {recs.map((r) => (
              <Card key={r.id} r={r} />
            ))}
          </AnimatePresence>
        )}
      </div>
    </section>
  );
}
