import { X } from 'lucide-react';
import { useCallback, useEffect, useState } from 'react';
import { cn } from '../../lib/cn';
import { dismiss, isDismissed, subscribe } from '../../lib/onboarding';
import { Callout, type CalloutTone } from './Callout';

interface HintProps {
  /** Stable namespaced id, e.g. "empty.first_chat" or "obsidian.first_open". */
  id: string;
  tone?: CalloutTone;
  title?: React.ReactNode;
  className?: string;
  /**
   * When false, render as plain Callout — no dismiss + no persistence.
   * Useful for previewing in storybook/admin replay.
   */
  persistent?: boolean;
  children?: React.ReactNode;
  onDismiss?: () => void;
}

/**
 * One-shot, dismissible coaching callout.
 *
 * Renders nothing once `id` is in the onboarding.dismissed set. Persists across
 * sessions via localStorage. Subscribes to changes so a "Replay tour" action
 * elsewhere can re-enable hints without a reload.
 */
export function Hint({
  id,
  tone = 'info',
  title,
  className,
  persistent = true,
  children,
  onDismiss,
}: HintProps) {
  const [dismissed, setDismissed] = useState(() => (persistent ? isDismissed(id) : false));

  useEffect(() => {
    if (!persistent) return;
    setDismissed(isDismissed(id));
    return subscribe(() => setDismissed(isDismissed(id)));
  }, [id, persistent]);

  const handleDismiss = useCallback(() => {
    if (persistent) dismiss(id);
    setDismissed(true);
    onDismiss?.();
  }, [id, onDismiss, persistent]);

  if (dismissed) return null;

  return (
    <div className={cn('relative', className)}>
      <Callout tone={tone} title={title}>
        {children}
      </Callout>
      <button
        type="button"
        onClick={handleDismiss}
        aria-label="nascondi suggerimento"
        className="focus-ring absolute right-1.5 top-1.5 grid size-6 place-items-center rounded-md
                   text-ink-subtle hover:bg-[var(--color-surface-raised)] hover:text-ink"
      >
        <X size={12} aria-hidden />
      </button>
    </div>
  );
}
