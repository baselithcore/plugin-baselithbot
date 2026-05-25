import { ReactNode } from 'react';
import { Icon } from './Icon';

type Trend = 'up' | 'down' | 'flat';
type Tone = 'neutral' | 'critical' | 'warn' | 'good' | 'brand';

interface StatProps {
  label: string;
  value: ReactNode;
  delta?: { value: string; trend: Trend; positive?: boolean };
  hint?: ReactNode;
  icon?: ReactNode;
  tone?: Tone;
}

const TONE_VALUE: Record<Tone, string> = {
  neutral: 'text-text-primary',
  critical: 'text-sev-critical',
  warn: 'text-accent-warn',
  good: 'text-status-success',
  brand: 'text-brand',
};

const TONE_ICON_BG: Record<Tone, string> = {
  neutral: 'bg-bg-overlay text-text-secondary',
  critical: 'bg-sev-critical/10 text-sev-critical',
  warn: 'bg-accent-warn/10 text-accent-warn',
  good: 'bg-status-success/10 text-status-success',
  brand: 'bg-brand/10 text-brand',
};

export function Stat({ label, value, delta, hint, icon, tone = 'neutral' }: StatProps) {
  const trendColor =
    delta?.trend === 'up'
      ? delta.positive === false
        ? 'text-sev-critical'
        : 'text-status-success'
      : delta?.trend === 'down'
        ? delta.positive === false
          ? 'text-status-success'
          : 'text-sev-critical'
        : 'text-text-muted';

  return (
    <div className="ra-card ra-card-hover px-5 py-4">
      <div className="flex items-start justify-between gap-3">
        <p className="ra-section-title">{label}</p>
        {icon && (
          <div className={`grid h-7 w-7 place-items-center rounded ${TONE_ICON_BG[tone]}`}>
            {icon}
          </div>
        )}
      </div>
      <div className="mt-3 flex items-baseline gap-2">
        <span className={`font-display text-3xl font-medium tabular-nums ${TONE_VALUE[tone]}`}>
          {value}
        </span>
        {delta && (
          <span
            className={`inline-flex items-center gap-0.5 text-xs font-mono font-medium ${trendColor}`}
          >
            {delta.trend === 'up' && <Icon.ArrowUp size={12} />}
            {delta.trend === 'down' && <Icon.ArrowDown size={12} />}
            {delta.value}
          </span>
        )}
      </div>
      {hint && <p className="mt-1 text-xs text-text-muted">{hint}</p>}
    </div>
  );
}
