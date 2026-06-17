import { useTranslation } from 'react-i18next';
import type { PluginState } from '@/types';

const TONE: Record<PluginState, string> = {
  active: 'border-emerald-500/25 bg-emerald-500/10 text-emerald-500',
  discovered: 'border-sky-500/25 bg-sky-500/10 text-sky-500',
  disabled: 'border-[var(--border)] surf t-dim',
  failed: 'border-rose-500/25 bg-rose-500/10 text-rose-500',
  unknown: 'border-[var(--border)] surf t-faint',
};

// Distinct shape per state so status reads without relying on color alone
// (colorblind accessibility).
const SHAPE: Record<PluginState, string> = {
  active: '●',
  discovered: '◆',
  disabled: '■',
  failed: '▲',
  unknown: '○',
};

interface Props {
  state: PluginState;
  title?: string; // hover detail: latency + code + last seen
}

export function HealthBadge({ state, title }: Props) {
  const { t } = useTranslation();
  const dot = state === 'active' ? 'status-pulse' : '';

  return (
    <span
      title={title}
      className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide ${TONE[state]}`}
    >
      <span aria-hidden className={`text-[0.7em] leading-none ${dot}`}>
        {SHAPE[state]}
      </span>
      {t(`state.${state}`)}
    </span>
  );
}
