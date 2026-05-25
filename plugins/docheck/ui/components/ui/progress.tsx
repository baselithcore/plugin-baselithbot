'use client';

import { cn } from '@/lib/cn';

interface Props {
  value: number;
  max?: number;
  className?: string;
  indeterminate?: boolean;
  tone?: 'info' | 'success' | 'warning' | 'danger';
}

const TONE = {
  info: 'bg-status-info',
  success: 'bg-status-success',
  warning: 'bg-status-warning',
  danger: 'bg-status-danger',
} as const;

export function Progress({ value, max = 100, className, indeterminate, tone = 'info' }: Props) {
  const pct = indeterminate ? 100 : Math.min(100, Math.max(0, (value / max) * 100));
  return (
    <div
      role="progressbar"
      aria-valuemin={0}
      aria-valuemax={max}
      aria-valuenow={indeterminate ? undefined : value}
      className={cn(
        'relative h-1.5 w-full overflow-hidden rounded-full bg-border-subtle',
        className
      )}
    >
      {indeterminate ? (
        <div className="absolute inset-0 stripe-loading" />
      ) : (
        <div
          className={cn(
            'h-full rounded-full transition-[width] duration-300 ease-smooth',
            TONE[tone]
          )}
          style={{ width: `${pct}%` }}
        />
      )}
    </div>
  );
}
