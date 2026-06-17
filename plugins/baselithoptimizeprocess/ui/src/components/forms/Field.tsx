import { Info } from 'lucide-react';
import type { ReactNode } from 'react';

import { cn } from '../../lib/ui';

interface FieldProps {
  /** Human label — always visible (no placeholder-as-label). */
  label: string;
  /** One-line plain-language explanation shown under the control. */
  hint?: string;
  /** Marks the field required with a subtle accent dot. */
  required?: boolean;
  /** Optional unit/suffix shown inline at the right of the label row. */
  suffix?: string;
  className?: string;
  children: ReactNode;
}

/**
 * Labeled form field with an always-visible label and an optional plain-language
 * hint — the building block for self-explanatory ("parlante") forms.
 */
export function Field({ label, hint, required, suffix, className, children }: FieldProps) {
  return (
    <label className={cn('flex flex-col gap-1.5', className)}>
      <span className="flex items-center justify-between gap-2">
        <span className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
          {label}
          {required && (
            <span className="ml-1 text-accent-soft" aria-hidden="true">
              •
            </span>
          )}
        </span>
        {suffix && <span className="text-[10px] font-medium text-slate-500">{suffix}</span>}
      </span>
      {children}
      {hint && <span className="text-[11px] leading-snug text-slate-500">{hint}</span>}
    </label>
  );
}

/** Inline jargon helper — an info dot with a hover tooltip. */
export function InfoTip({ text }: { text: string }) {
  return (
    <span
      className="inline-flex cursor-help text-slate-500 hover:text-slate-300"
      title={text}
      aria-label={text}
    >
      <Info size={13} aria-hidden="true" />
    </span>
  );
}
