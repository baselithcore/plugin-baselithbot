// Compact KPI row summarising the twin's state at a glance.

import { useTranslation } from 'react-i18next';
import { Brain, ListChecks, ShieldCheck, Sparkles } from 'lucide-react';
import type { TwinStatus } from '../api/types';

function Stat({
  icon,
  label,
  value,
  hint,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  hint?: string;
}) {
  return (
    <div className="rounded-2xl border border-white/5 bg-ink-800/70 p-4 backdrop-blur-xl">
      <div className="flex items-center gap-2 text-white/40">
        {icon}
        <span className="text-xs font-medium uppercase tracking-wider">{label}</span>
      </div>
      <p className="mt-2 text-2xl font-semibold text-white">{value}</p>
      {hint && <p className="mt-0.5 text-xs text-white/40">{hint}</p>}
    </div>
  );
}

export function StatCards({ status }: { status: TwinStatus | null }) {
  const { t } = useTranslation();
  const styleHint = status?.style_trained
    ? t('stat.style.trained', { count: status.style_messages })
    : t('stat.style.untrained');
  return (
    <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
      <Stat
        icon={<Sparkles className="h-4 w-4" />}
        label={t('stat.style')}
        value={status?.style_trained ? '✓' : '—'}
        hint={styleHint}
      />
      <Stat
        icon={<ShieldCheck className="h-4 w-4" />}
        label={t('stat.whitelist')}
        value={status?.whitelist_size ?? 0}
      />
      <Stat
        icon={<ListChecks className="h-4 w-4" />}
        label={t('stat.pending')}
        value={status?.pending_replies ?? 0}
      />
      <Stat
        icon={<Brain className="h-4 w-4" />}
        label={t('stat.facts')}
        value={status?.salient_facts ?? 0}
      />
    </div>
  );
}
