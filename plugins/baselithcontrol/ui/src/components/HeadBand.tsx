import { useTranslation } from 'react-i18next';
import type { PluginCard as Card } from '@/types';
import type { Tone } from '@/lib/format';
import { AnimatedNumber } from '@/components/widgets/AnimatedNumber';

const VALUE: Record<Tone, string> = {
  neutral: 't-primary',
  success: 'text-emerald-500',
  warning: 'text-amber-500',
  danger: 'text-rose-500',
  info: 'text-sky-500',
};

const DOT: Record<Tone, string> = {
  neutral: 'bg-[var(--text-faint)]',
  success: 'bg-emerald-500',
  warning: 'bg-amber-500',
  danger: 'bg-rose-500',
  info: 'bg-sky-500',
};

interface Stat {
  key: string;
  value: number;
  tone: Tone;
}

// Compact KPI ribbon above the grid. Derived from the SAME live card store as
// the filter bar/insights so counts stay mutually consistent and update
// instantly on enable/disable. Health is state-gated: only *active* plugins
// count as healthy/degraded. Renders frameless — the caller frames it.
export function HeadBand({ cards }: { cards: Card[] }) {
  const { t } = useTranslation();

  const stats: Stat[] = [
    { key: 'total', value: cards.length, tone: 'neutral' },
    {
      key: 'healthy',
      value: cards.filter((c) => c.state === 'active' && c.healthy === true).length,
      tone: 'success',
    },
    {
      key: 'degraded',
      value: cards.filter((c) => c.state === 'active' && c.healthy === false).length,
      tone: 'warning',
    },
    {
      key: 'down',
      value: cards.filter((c) => c.state === 'failed').length,
      tone: 'danger',
    },
  ];

  return (
    <>
      {stats.map((s) => {
        // A zero degraded/down count reads as neutral, not alarming.
        const tone: Tone =
          s.value === 0 && (s.key === 'degraded' || s.key === 'down') ? 'neutral' : s.tone;
        return (
          <div
            key={s.key}
            className="flex items-center justify-between gap-2 bg-[var(--surface-1)] px-4 py-2.5"
          >
            <div className="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wide t-faint">
              <span className={`h-1.5 w-1.5 rounded-full ${DOT[tone]}`} />
              {t(`head.${s.key}`)}
            </div>
            <AnimatedNumber
              value={s.value}
              className={`font-display text-[1.3rem] font-bold leading-none tabular-nums ${VALUE[tone]}`}
            />
          </div>
        );
      })}
    </>
  );
}
