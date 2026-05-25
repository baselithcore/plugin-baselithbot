import type { ComponentType, ReactNode } from 'react';

export const HEX_RE = /^#[0-9A-Fa-f]{6}$/;

export function SubHeader({
  title,
  icon: Icon,
}: {
  title: string;
  icon?: ComponentType<{ size?: number; className?: string; 'aria-hidden'?: boolean }>;
}) {
  return (
    <div className="flex items-center gap-1.5 text-[11.5px] font-semibold text-ink">
      {Icon ? <Icon size={13} className="text-[var(--color-brand)]" aria-hidden /> : null}
      {title}
    </div>
  );
}

export function Field({
  label,
  hint,
  children,
}: {
  label: string;
  hint?: string;
  children: ReactNode;
}) {
  return (
    <div className="space-y-1">
      <label className="block text-[10px] font-medium uppercase tracking-wide text-ink-subtle">
        {label}
      </label>
      {children}
      {hint ? <p className="text-[10px] leading-snug text-ink-subtle">{hint}</p> : null}
    </div>
  );
}

export function ColorField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="space-y-1">
      <label className="block text-[10px] font-medium uppercase tracking-wide text-ink-subtle">
        {label}
      </label>
      <div className="flex items-center gap-1.5">
        <input
          type="color"
          value={value && HEX_RE.test(value) ? value : '#1d4f91'}
          onChange={(e) => onChange(e.target.value)}
          aria-label={`picker ${label}`}
          className="size-7 cursor-pointer rounded-md border border-[var(--color-border)] bg-transparent"
        />
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="#1d4f91"
          spellCheck={false}
          className="input-text flex-1 font-mono text-[10.5px]"
        />
      </div>
    </div>
  );
}

export function BrandingInputStyle() {
  return (
    <style>{`
      .input-text {
        width: 100%;
        border-radius: 0.375rem;
        border: 1px solid var(--color-border);
        background-color: var(--color-canvas);
        padding: 0.25rem 0.5rem;
        font-size: 11px;
        color: var(--color-ink);
        font-family: inherit;
      }
      .input-text:focus { outline: none; box-shadow: 0 0 0 1px var(--color-accent); }
      textarea.input-text { resize: vertical; min-height: 1.75rem; }
    `}</style>
  );
}
