import { forwardRef } from 'react';
import { Loader2 } from 'lucide-react';
import { cn } from '../../lib/cn';

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
export type ButtonSize = 'sm' | 'md';

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  /** Optional icon rendered before children. Pass a Lucide component. */
  leadingIcon?: React.ComponentType<{ size?: number; className?: string }>;
  trailingIcon?: React.ComponentType<{ size?: number; className?: string }>;
}

const VARIANTS: Record<ButtonVariant, string> = {
  primary:
    'bg-[var(--color-brand)] text-white hover:bg-[var(--color-brand-strong)] disabled:opacity-40',
  secondary:
    'border border-[var(--color-border)] bg-[var(--color-canvas-raised)] text-ink-muted shadow-xs hover:border-[var(--color-border-strong)] hover:bg-[var(--color-surface)] hover:text-ink',
  ghost: 'text-ink-muted hover:bg-[var(--color-surface)] hover:text-ink',
  danger:
    'border border-[var(--color-danger)]/40 bg-[var(--color-danger)]/10 text-[var(--color-danger)] hover:bg-[var(--color-danger)]/15',
};

const SIZES: Record<ButtonSize, string> = {
  sm: 'min-h-7 px-2.5 text-[11px]',
  md: 'min-h-9 px-3.5 text-xs',
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    variant = 'primary',
    size = 'md',
    loading = false,
    leadingIcon: LeadingIcon,
    trailingIcon: TrailingIcon,
    disabled,
    className,
    children,
    type = 'button',
    ...rest
  },
  ref
) {
  const iconSize = size === 'sm' ? 11 : 12;
  return (
    <button
      ref={ref}
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cn(
        'focus-ring inline-flex items-center justify-center gap-1.5 rounded-lg font-semibold',
        'transition-colors disabled:cursor-not-allowed',
        SIZES[size],
        VARIANTS[variant],
        className
      )}
      {...rest}
    >
      {loading ? (
        <Loader2 size={iconSize} className="animate-spin" />
      ) : LeadingIcon ? (
        <LeadingIcon size={iconSize} />
      ) : null}
      {children}
      {!loading && TrailingIcon && <TrailingIcon size={iconSize} />}
    </button>
  );
});
