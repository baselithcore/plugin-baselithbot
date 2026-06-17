import type { LucideIcon } from 'lucide-react';
import { Sparkline } from '../Sparkline';

interface Props {
  icon: LucideIcon;
  label: string;
  value: string;
  sub?: string;
  percent?: number | null; // 0–100 → renders a fill bar; tone shifts when high
  spark?: number[];
  id: string;
}

function barTone(pct: number): string {
  if (pct >= 90) return 'bg-rose-500';
  if (pct >= 70) return 'bg-amber-500';
  return 'bg-emerald-500';
}

// One resource gauge: headline value plus either a percent fill bar or a
// trend sparkline. Used for CPU, memory, network and process counters.
export function GaugeCard({ icon: Icon, label, value, sub, percent, spark, id }: Props) {
  return (
    <div className="glass flex flex-col gap-2 rounded-xl p-4">
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4 t-faint" />
        <span className="text-[11px] font-semibold uppercase tracking-wider t-faint">{label}</span>
      </div>

      <div className="flex items-baseline gap-1.5">
        <span className="font-mono text-xl font-semibold tabular-nums t-primary">{value}</span>
        {sub && <span className="text-[11px] font-medium t-dim">{sub}</span>}
      </div>

      {typeof percent === 'number' ? (
        <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-[var(--surface-inset)]">
          <div
            className={`h-full rounded-full transition-all duration-500 ${barTone(percent)}`}
            style={{ width: `${Math.min(100, Math.max(0, percent))}%` }}
          />
        </div>
      ) : spark ? (
        <Sparkline data={spark} id={id} />
      ) : null}
    </div>
  );
}
