import { forwardRef } from 'react';
import { cn } from '../../lib/cn';

interface IconButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  /** Lucide-like component, rendered at the configured size. */
  icon: React.ComponentType<{ size?: number; className?: string }>;
  /** Required for screen readers — icon-only buttons need a label. */
  'aria-label': string;
  size?: 'sm' | 'md' | 'lg';
  /** Visual emphasis. `subtle` uses transparent border, `outline` always shows it. */
  emphasis?: 'subtle' | 'outline';
}

const BOX = {
  sm: 'size-7',
  md: 'size-8',
  lg: 'size-9',
} as const;

const ICON_SIZE = { sm: 12, md: 13, lg: 15 } as const;

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(function IconButton(
  { icon: Icon, size = 'md', emphasis = 'subtle', className, type = 'button', ...rest },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={cn(
        'focus-ring inline-flex items-center justify-center rounded-lg text-ink-subtle transition-colors',
        'hover:border-[var(--color-border)] hover:bg-[var(--color-surface)] hover:text-ink',
        'disabled:cursor-not-allowed disabled:opacity-40',
        emphasis === 'subtle'
          ? 'border border-transparent'
          : 'border border-[var(--color-border)] bg-[var(--color-canvas-raised)] shadow-xs',
        BOX[size],
        className,
      )}
      {...rest}
    >
      <Icon size={ICON_SIZE[size]} />
    </button>
  );
});
