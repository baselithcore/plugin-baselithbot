import { cn } from '../../lib/cn';

export function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'focus-ring relative rounded-t-lg px-3 py-2 text-xs font-semibold transition-colors',
        active
          ? 'bg-[var(--color-canvas-raised)] text-ink'
          : 'text-ink-subtle hover:bg-[var(--color-surface)] hover:text-ink'
      )}
    >
      {children}
      {active && (
        <span className="absolute inset-x-2 -bottom-px h-[2px] rounded-full bg-[var(--color-brand)]" />
      )}
    </button>
  );
}

export function OptionRow({
  label,
  hint,
  checked,
  onChange,
  warn,
}: {
  label: string;
  hint: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  warn?: boolean;
}) {
  return (
    <label
      className={cn(
        'flex cursor-pointer items-start gap-3 rounded-lg border border-[var(--color-border)] bg-[var(--color-canvas-raised)] px-3 py-2.5 hover:bg-[var(--color-surface)]'
      )}
    >
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-0.5 accent-[var(--color-brand)]"
      />
      <div className="min-w-0">
        <div className={cn('text-xs font-medium', warn && checked && 'text-amber-600')}>
          {label}
        </div>
        <div className="mt-0.5 text-[10.5px] text-ink-subtle leading-relaxed">{hint}</div>
      </div>
    </label>
  );
}
