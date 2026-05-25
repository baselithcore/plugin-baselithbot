import {
  type ComponentType,
  type InputHTMLAttributes,
  type ReactNode,
  useId,
} from 'react';

interface InfoPillProps {
  icon: ComponentType<{ size?: number; className?: string; 'aria-hidden'?: boolean }>;
  label: string;
  value: string;
}

export function InfoPill({ icon: Icon, label, value }: InfoPillProps) {
  return (
    <div className="min-w-0 rounded-lg border border-[var(--color-border)] bg-[var(--color-canvas-raised)] px-3 py-2 shadow-xs">
      <div className="flex items-center gap-2 text-[11px] text-ink-muted">
        <Icon size={13} className="shrink-0 text-[var(--color-brand)]" aria-hidden />
        <span className="truncate">{label}</span>
      </div>
      <div className="mt-1 truncate text-sm font-semibold text-ink" title={value}>
        {value}
      </div>
    </div>
  );
}

interface TabButtonProps {
  active: boolean;
  icon: ComponentType<{ size?: number; className?: string; 'aria-hidden'?: boolean }>;
  label: string;
  onClick: () => void;
}

export function TabButton({ active, icon: Icon, label, onClick }: TabButtonProps) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={onClick}
            className={`focus-ring inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border px-3 text-xs transition-all ${
        active
          ? 'border-[var(--color-brand)] bg-[var(--color-brand)] font-semibold text-white shadow-sm'
          : 'border-transparent font-medium text-ink-muted hover:border-[var(--color-border)] hover:bg-[var(--color-canvas-raised)] hover:text-ink'
      }`}
    >
      <Icon size={14} aria-hidden />
      {label}
    </button>
  );
}

export function PasswordMeter({ score }: { score: number }) {
  const label =
    score >= 3 ? 'Buona' : score === 2 ? 'Media' : score === 1 ? 'Base' : 'Da impostare';
  return (
    <div aria-live="polite" className="-mt-2 rounded-md bg-[var(--color-surface)] px-3 py-2">
      <div className="mb-1.5 flex items-center justify-between gap-2 text-[11px]">
        <span className="font-medium text-ink-muted">Robustezza password</span>
        <span className="text-ink-muted">{label}</span>
      </div>
      <div className="grid grid-cols-3 gap-1" aria-hidden>
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className={`h-1 rounded-full ${
              i < score
                ? score >= 3
                  ? 'bg-[var(--color-success)]'
                  : score === 2
                    ? 'bg-[var(--color-warning)]'
                    : 'bg-[var(--color-danger)]'
                : 'bg-[var(--color-border)]'
            }`}
          />
        ))}
      </div>
    </div>
  );
}

interface FieldProps {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
  autoComplete?: string;
  autoFocus?: boolean;
  inputMode?: InputHTMLAttributes<HTMLInputElement>['inputMode'];
  placeholder?: string;
  required?: boolean;
  hint?: string;
  error?: string;
  icon?: ComponentType<{ size?: number; className?: string }>;
  trailing?: ReactNode;
}

export function Field({
  label,
  value,
  onChange,
  type = 'text',
  autoComplete,
  autoFocus,
  inputMode,
  placeholder,
  required,
  hint,
  error,
  icon: Icon,
  trailing,
}: FieldProps) {
  const id = useId();
  const hintId = `${id}-hint`;
  const errorId = `${id}-error`;
  const describedBy = error ? errorId : hint ? hintId : undefined;

  return (
    <div className="block">
      <label
        htmlFor={id}
        className="mb-1 block text-[11px] font-medium uppercase tracking-wider text-ink-muted"
      >
        {label}
      </label>
      <div className="relative">
        {Icon && (
          <Icon
            size={14}
            className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-subtle"
            aria-hidden
          />
        )}
        <input
          id={id}
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          autoComplete={autoComplete}
          autoFocus={autoFocus}
          inputMode={inputMode}
          placeholder={placeholder}
          required={required}
          aria-invalid={!!error || undefined}
          aria-describedby={describedBy}
          className={`w-full rounded-md border bg-[var(--color-canvas)] py-2 text-sm text-ink outline-none transition-colors focus-visible:ring-2 focus-visible:ring-[var(--color-brand-ring)] focus:border-[var(--color-brand)] ${
            Icon ? 'pl-9' : 'pl-3'
          } ${trailing ? 'pr-10' : 'pr-3'} ${
            error ? 'border-[var(--color-danger)]/60' : 'border-[var(--color-border)]'
          }`}
        />
        {trailing && (
          <div className="absolute right-2 top-1/2 -translate-y-1/2">{trailing}</div>
        )}
      </div>
      {hint && !error && (
        <span id={hintId} className="mt-1 block text-[11px] text-ink-muted">
          {hint}
        </span>
      )}
      {error && (
        <span
          id={errorId}
          role="alert"
          className="mt-1 block text-[11px] text-[var(--color-danger)]"
        >
          {error}
        </span>
      )}
    </div>
  );
}
