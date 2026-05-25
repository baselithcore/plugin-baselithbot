import { useId } from 'react';
import { cn } from '../../lib/cn';

interface SwitchProps {
  checked: boolean;
  onChange: (v: boolean) => void;
  /** Required: label for screen readers. Visually hidden if `hideLabel` is true. */
  label: string;
  /** Hidden label (visually) — pass true when label is rendered separately. */
  hideLabel?: boolean;
  disabled?: boolean;
  /** Optional description id for aria-describedby */
  describedBy?: string;
}

export function Switch({ checked, onChange, label, hideLabel, disabled, describedBy }: SwitchProps) {
  const id = useId();
  return (
    <button
      id={id}
      role="switch"
      type="button"
      aria-checked={checked}
      aria-label={hideLabel ? label : undefined}
      aria-describedby={describedBy}
      disabled={disabled}
      onClick={() => !disabled && onChange(!checked)}
      className={cn(
        'focus-ring relative inline-flex h-5 w-9 shrink-0 items-center rounded-full border transition-colors',
        'disabled:cursor-not-allowed disabled:opacity-40',
        checked
          ? 'border-transparent bg-[var(--color-brand)]'
          : 'border-[var(--color-border)] bg-[var(--color-surface)]',
      )}
    >
      <span
        aria-hidden
        className={cn(
          'absolute top-[1px] size-[14px] rounded-full bg-white shadow-sm transition-transform',
          checked ? 'translate-x-[19px]' : 'translate-x-[1px]',
        )}
      />
    </button>
  );
}
