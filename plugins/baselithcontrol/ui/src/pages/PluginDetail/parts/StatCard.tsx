import type { ReactNode } from 'react';
import type { Tone } from '@/lib/format';

const VALUE_TONE: Record<Tone, string> = {
  neutral: 't-primary',
  success: 'text-emerald-500',
  warning: 'text-amber-500',
  danger: 'text-rose-500',
  info: 'text-sky-500',
};

interface Props {
  label: string;
  value: string;
  unit?: string;
  tone?: Tone;
  icon?: ReactNode;
  children?: ReactNode; // optional sparkline / trend, pinned to the card foot
}

// Big-number KPI tile: a single metric reads at a glance, hairline-bordered,
// flat. The numeric value is the visual anchor (large, tabular, mono); the
// label sits quiet above it. Optional `children` render a sparkline at the foot.
export function StatCard({ label, value, unit, tone = 'neutral', icon, children }: Props) {
  return (
    <div className="glass flex flex-col gap-2 p-4">
      <div className="flex items-center justify-between gap-2">
        <span className="text-[10px] font-semibold uppercase tracking-wider t-faint">{label}</span>
        {icon && <span className="t-faint">{icon}</span>}
      </div>
      <div className="flex items-baseline gap-1">
        <span
          className={`font-mono text-[1.6rem] font-semibold leading-none tabular-nums ${VALUE_TONE[tone]}`}
        >
          {value}
        </span>
        {unit && <span className="text-[11px] font-medium t-faint">{unit}</span>}
      </div>
      {children && <div className="mt-auto pt-1">{children}</div>}
    </div>
  );
}
