import { AlertCircle } from 'lucide-react';
import {
  Children,
  cloneElement,
  isValidElement,
  useId,
  type ReactElement,
} from 'react';
import { cn } from '../../lib/cn';

interface FieldProps {
  label: string;
  hint?: string;
  error?: string;
  children: React.ReactNode;
  full?: boolean;
  /** Optional id for the input. Generated if missing. */
  htmlFor?: string;
}

/**
 * Form field wrapper that wires aria-describedby + aria-invalid into the
 * single input/select/textarea passed as a child. Hints and errors get a
 * stable id so screen readers announce them when focus enters the field.
 */
export function Field({ label, hint, error, children, full, htmlFor }: FieldProps) {
  const generated = useId();
  const inputId = htmlFor ?? generated;
  const hintId = `${inputId}-hint`;
  const errorId = `${inputId}-error`;

  const enhanced = Children.map(children, (child) => {
    if (!isValidElement(child)) return child;
    const c = child as ReactElement<Record<string, unknown>>;
    const describedBy = error ? errorId : hint ? hintId : undefined;
    return cloneElement(c, {
      id: c.props.id ?? inputId,
      'aria-invalid': error ? true : c.props['aria-invalid'],
      'aria-describedby':
        [c.props['aria-describedby'] as string | undefined, describedBy]
          .filter(Boolean)
          .join(' ') || undefined,
    });
  });

  return (
    <div className={cn('flex flex-col gap-1', full && 'sm:col-span-2')}>
      <label htmlFor={inputId} className="text-[10.5px] font-semibold text-ink">
        {label}
      </label>
      {enhanced}
      {hint && !error && (
        <span id={hintId} className="text-[10px] text-ink-subtle leading-relaxed">
          {hint}
        </span>
      )}
      {error && (
        <span id={errorId} role="alert" className="text-[10px] text-[var(--color-danger)]">
          <AlertCircle size={9} className="inline-block mr-1 -mt-0.5" aria-hidden />
          {error}
        </span>
      )}
    </div>
  );
}

export function Row({ k, v }: { k: string; v: string }) {
  return (
    <>
      <dt className="text-ink-subtle">{k}</dt>
      <dd className="text-ink truncate" title={v}>
        {v}
      </dd>
    </>
  );
}

export function IdentityStepSkeleton() {
  return (
    <div className="px-5 py-4 space-y-5 animate-pulse" aria-busy="true" aria-label="caricamento">
      <div>
        <div className="h-3 w-32 bg-[var(--color-surface)] rounded mb-2" />
        <div className="space-y-2">
          {[0, 1, 2].map((i) => (
            <div key={i} className="h-12 rounded-lg bg-[var(--color-surface)]" />
          ))}
        </div>
      </div>
      <div>
        <div className="h-3 w-40 bg-[var(--color-surface)] rounded mb-2" />
        <div className="grid grid-cols-2 gap-3">
          <div className="h-9 rounded bg-[var(--color-surface)]" />
          <div className="h-9 rounded bg-[var(--color-surface)]" />
          <div className="h-9 rounded bg-[var(--color-surface)] col-span-2" />
        </div>
      </div>
    </div>
  );
}

export interface StepProps {
  register: import('react-hook-form').UseFormRegister<import('./schema').WizardForm>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  control?: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  errors: any;
  values?: import('./schema').WizardForm;
}
