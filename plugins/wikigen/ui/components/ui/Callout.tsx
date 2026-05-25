import { AlertCircle, AlertTriangle, CheckCircle2, Info, type LucideIcon } from 'lucide-react';
import { cn } from '../../lib/cn';

export type CalloutTone = 'neutral' | 'info' | 'success' | 'warning' | 'danger';

interface CalloutProps {
  tone?: CalloutTone;
  /** Optional title rendered as bold first row. */
  title?: React.ReactNode;
  /** Override icon. Defaults from tone. Pass `null` to omit. */
  icon?: LucideIcon | null;
  className?: string;
  children?: React.ReactNode;
}

const TONE: Record<
  CalloutTone,
  { box: string; icon: string; defaultIcon: LucideIcon | null; role?: 'alert' | 'status' }
> = {
  neutral: {
    box: 'border-[var(--color-border)] bg-[var(--color-surface)]',
    icon: 'text-ink-subtle',
    defaultIcon: null,
  },
  info: {
    box: 'border-[var(--color-brand-ring)] bg-[var(--color-brand-soft)]',
    icon: 'text-[var(--color-brand)]',
    defaultIcon: Info,
    role: 'status',
  },
  success: {
    box: 'border-emerald-500/30 bg-emerald-500/8 dark:bg-emerald-500/10',
    icon: 'text-emerald-600 dark:text-emerald-400',
    defaultIcon: CheckCircle2,
    role: 'status',
  },
  warning: {
    box: 'border-amber-500/40 bg-amber-500/8 dark:bg-amber-500/10',
    icon: 'text-amber-600 dark:text-amber-400',
    defaultIcon: AlertTriangle,
    role: 'status',
  },
  danger: {
    box: 'border-rose-500/40 bg-rose-500/8 dark:bg-rose-500/10',
    icon: 'text-rose-600 dark:text-rose-400',
    defaultIcon: AlertCircle,
    role: 'alert',
  },
};

export function Callout({ tone = 'neutral', title, icon, className, children }: CalloutProps) {
  const t = TONE[tone];
  const Icon = icon === null ? null : (icon ?? t.defaultIcon);
  return (
    <div
      role={t.role}
      className={cn(
        'rounded-lg border px-3 py-2.5 text-[11.5px] leading-relaxed',
        t.box,
        className
      )}
    >
      <div className="flex items-start gap-2.5">
        {Icon && <Icon size={13} className={cn('mt-0.5 shrink-0', t.icon)} aria-hidden />}
        <div className="min-w-0 flex-1">
          {title && (
            <div className={cn('text-[12px] font-semibold text-ink', children && 'mb-1')}>
              {title}
            </div>
          )}
          {children && <div className="text-ink-muted">{children}</div>}
        </div>
      </div>
    </div>
  );
}
