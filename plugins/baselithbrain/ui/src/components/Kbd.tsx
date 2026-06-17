import { cn } from '@/lib/cn';

/** A keyboard-key chip. Used everywhere shortcuts are surfaced (Linear-style). */
export function Kbd({ keys, className }: { keys: string; className?: string }) {
  return (
    <kbd
      className={cn(
        'inline-flex items-center gap-0.5 rounded-md border border-[var(--color-border)]',
        'bg-[var(--color-surface)] px-1.5 py-0.5 font-mono text-[10px] font-medium',
        'text-[var(--color-muted)] shadow-[0_1px_0_var(--color-border)]',
        className
      )}
    >
      {keys}
    </kbd>
  );
}

/** Platform-aware modifier label (⌘ on mac, Ctrl elsewhere). */
export const MOD =
  typeof navigator !== 'undefined' && /Mac|iP/.test(navigator.platform) ? '⌘' : 'Ctrl';
