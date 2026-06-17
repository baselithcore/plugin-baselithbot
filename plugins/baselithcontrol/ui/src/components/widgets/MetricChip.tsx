import type { Tone } from '@/lib/format';

const TONE: Record<Tone, string> = {
  neutral: 'surf t-dim',
  success: 'bg-emerald-500/10 text-emerald-500',
  warning: 'bg-amber-500/10 text-amber-500',
  danger: 'bg-rose-500/10 text-rose-500',
  info: 'bg-sky-500/10 text-sky-500',
};

interface Props {
  label: string;
  value: string;
  tone?: Tone;
}

export function MetricChip({ label, value, tone = 'neutral' }: Props) {
  return (
    <div
      className={`flex items-baseline justify-between gap-3 rounded-md px-2.5 py-1.5 ${TONE[tone]}`}
    >
      <span className="text-[12px] t-dim">{label}</span>
      <span className="font-mono text-[13px] font-semibold tabular-nums">{value}</span>
    </div>
  );
}
