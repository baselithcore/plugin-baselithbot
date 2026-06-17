import { Activity, AlertTriangle, CircleDashed, PauseCircle, ShieldCheck } from 'lucide-react';
import { motion } from 'motion/react';
import { useTranslation } from 'react-i18next';
import { spring } from '@/lib/motion';
import type { PluginState } from '@/types';

type StateFilter = PluginState | 'all';

interface Props {
  counts: Record<StateFilter, number>;
  value: StateFilter;
  onChange: (value: StateFilter) => void;
}

const OPTIONS: { value: StateFilter; icon: typeof Activity }[] = [
  { value: 'all', icon: Activity },
  { value: 'active', icon: ShieldCheck },
  { value: 'failed', icon: AlertTriangle },
  { value: 'disabled', icon: PauseCircle },
  { value: 'discovered', icon: CircleDashed },
];

export function StatusFilterBar({ counts, value, onChange }: Props) {
  const { t } = useTranslation();

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {OPTIONS.map(({ value: option, icon: Icon }) => {
        const active = value === option;
        const label = option === 'all' ? t('filter.all_status') : t(`state.${option}`);
        return (
          <button
            key={option}
            type="button"
            onClick={() => onChange(option)}
            aria-pressed={active}
            className={`relative inline-flex min-h-8 items-center gap-2 rounded-md px-2.5 text-[12px] font-medium transition-colors ${
              active ? 't-accent' : 't-dim hover:bg-[var(--surface-2)] hover:text-[var(--text)]'
            }`}
          >
            {active && (
              <motion.span
                layoutId="status-pill"
                transition={spring}
                className="absolute inset-0 rounded-md bg-[var(--accent-soft)]"
              />
            )}
            <Icon className="relative z-10 h-3.5 w-3.5" />
            <span className="relative z-10">{label}</span>
            <span className="relative z-10 rounded bg-[var(--surface-inset)] px-1.5 py-0.5 text-[10px] tabular-nums t-faint">
              {counts[option]}
            </span>
          </button>
        );
      })}
    </div>
  );
}
