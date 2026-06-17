import type { LucideIcon } from 'lucide-react';

import { cn, formatNumber } from '../../lib/ui';

export type StatTone = 'neutral' | 'accent' | 'good' | 'warning' | 'critical';

export interface StatItem {
  label: string;
  value: number | string;
  detail: string;
  icon: LucideIcon;
  tone?: StatTone;
}

const VALUE_TONE: Record<StatTone, string> = {
  neutral: 'text-slate-100',
  accent: 'text-accent-soft',
  good: 'text-sev-low',
  warning: 'text-sev-medium',
  critical: 'text-sev-critical',
};

const ICON_TONE: Record<StatTone, string> = {
  neutral: 'bg-white/[0.05] text-slate-400',
  accent: 'bg-accent/10 text-accent-soft',
  good: 'bg-sev-low/10 text-sev-low',
  warning: 'bg-sev-medium/10 text-sev-medium',
  critical: 'bg-sev-critical/10 text-sev-critical',
};

/** Compact metric overview rendered as an even grid of stat cards. */
export function StatStrip({ stats }: { stats: StatItem[] }) {
  return (
    <div className="mt-4 grid grid-cols-2 gap-2.5 sm:grid-cols-3 xl:grid-cols-5">
      {stats.map((stat) => (
        <StatCard key={stat.label} {...stat} />
      ))}
    </div>
  );
}

function StatCard({ label, value, detail, icon: Icon, tone = 'neutral' }: StatItem) {
  return (
    <div className="glass glass-hover flex items-center gap-3 p-3">
      <span className={cn('grid h-9 w-9 shrink-0 place-items-center rounded-lg', ICON_TONE[tone])}>
        <Icon size={17} strokeWidth={2} aria-hidden="true" />
      </span>
      <div className="min-w-0">
        <p className="truncate text-[11px] font-medium uppercase tracking-wide text-slate-500">
          {label}
        </p>
        <p className={cn('number text-lg font-semibold leading-tight', VALUE_TONE[tone])}>
          {typeof value === 'number' ? formatNumber(value) : value}
        </p>
        <p className="truncate text-[11px] text-slate-500">{detail}</p>
      </div>
    </div>
  );
}
