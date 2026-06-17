// Style profile panel: quantitative metrics, frequent expressions, and authentic
// exemplars of how the owner writes, with a retrain action.

import { useTranslation } from 'react-i18next';
import { RefreshCw } from 'lucide-react';
import type { StyleProfile } from '../api/types';
import { Badge, Button, Card } from './ui';

function Meter({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <div className="flex justify-between text-xs text-white/50">
        <span>{label}</span>
        <span>{(value * 100).toFixed(0)}%</span>
      </div>
      <div className="mt-1 h-1.5 rounded-full bg-white/5">
        <div
          className="h-full rounded-full bg-gradient-to-r from-brand-500 to-accent-500"
          style={{ width: `${Math.min(100, value * 100)}%` }}
        />
      </div>
    </div>
  );
}

export function StylePanel({
  style,
  onTrain,
}: {
  style: StyleProfile | null;
  onTrain: () => void;
}) {
  const { t } = useTranslation();
  const action = (
    <Button onClick={onTrain}>
      <RefreshCw className="mr-1 inline h-3.5 w-3.5" />
      {t('style.train')}
    </Button>
  );
  if (!style || !style.trained) {
    return (
      <Card title={t('style.title')} action={action}>
        <p className="py-6 text-center text-sm text-white/30">{t('style.untrained')}</p>
      </Card>
    );
  }
  const m = style.metrics;
  return (
    <Card title={t('style.title')} action={action}>
      <div className="space-y-3">
        <Meter label={t('style.formality')} value={m.formality} />
        <Meter label={t('style.emoji')} value={Math.min(1, m.emoji_rate)} />
        <Meter label={t('style.questions')} value={m.question_rate} />
        <div className="flex flex-wrap items-center gap-2 pt-1 text-xs text-white/50">
          <Badge tone="brand">
            {t('style.locale')}: {m.dominant_locale.toUpperCase()}
          </Badge>
          <Badge>
            {t('style.length')}: {m.avg_words_per_message}w
          </Badge>
          {m.top_emojis.slice(0, 5).map((e, i) => (
            <span key={i} className="text-base">
              {e}
            </span>
          ))}
        </div>
        {m.top_expressions.length > 0 && (
          <div>
            <p className="mb-1 text-xs text-white/40">{t('style.expressions')}</p>
            <div className="flex flex-wrap gap-1.5">
              {m.top_expressions.map((w, i) => (
                <Badge key={i}>{w}</Badge>
              ))}
            </div>
          </div>
        )}
        {style.exemplars.length > 0 && (
          <div>
            <p className="mb-1 text-xs text-white/40">{t('style.exemplars')}</p>
            <ul className="space-y-1 text-sm text-white/60">
              {style.exemplars.slice(0, 4).map((ex, i) => (
                <li key={i} className="rounded-lg bg-white/[0.02] px-2.5 py-1.5">
                  “{ex.text}”
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </Card>
  );
}
