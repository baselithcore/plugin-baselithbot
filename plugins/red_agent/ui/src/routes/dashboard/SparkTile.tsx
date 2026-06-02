import { Sparkline } from '../../components/ui';

interface SparkTileProps {
  label: string;
  value: number | string;
  hint: string;
  series: number[];
  color: string;
  tone?: 'neutral' | 'warn' | 'critical';
}

const SPARK_TONE: Record<NonNullable<SparkTileProps['tone']>, string> = {
  neutral: 'text-text-primary',
  warn: 'text-accent-warn',
  critical: 'text-sev-critical',
};

export function SparkTile({ label, value, hint, series, color, tone = 'neutral' }: SparkTileProps) {
  return (
    <div className="ra-card flex flex-col p-4">
      <p className="ra-section-title">{label}</p>
      <div className="mt-2 flex items-baseline justify-between gap-3">
        <span className={`font-display text-3xl font-medium tabular-nums ${SPARK_TONE[tone]}`}>
          {value}
        </span>
      </div>
      <p className="mt-0.5 text-2xs text-text-muted">{hint}</p>
      <div className="mt-2">
        <Sparkline data={series} color={color} height={42} />
      </div>
    </div>
  );
}
