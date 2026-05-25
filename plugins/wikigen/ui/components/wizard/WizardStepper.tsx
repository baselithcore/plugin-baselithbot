import {
  Building2,
  CheckCircle2,
  Database,
  FileText,
  KeyRound,
  Palette,
  ShieldCheck,
} from 'lucide-react';
import { cn } from '../../lib/cn';
import { STEPS, type Step } from './schema';

/**
 * Visual stepper for the wizard. Steps already passed are clickable
 * (jump back); future steps require validation and are disabled.
 */
export function WizardStepper({ step, onJump }: { step: Step; onJump: (s: Step) => void }) {
  const stepIdx = STEPS.findIndex((s) => s.id === step);
  const pct = Math.round(((stepIdx + 1) / STEPS.length) * 100);

  return (
    <nav
      className="border-b border-[var(--color-border)] bg-[var(--color-canvas-raised)] px-4 py-3 sm:px-5"
      aria-label="progresso wizard"
    >
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="text-[10px] font-semibold uppercase text-ink-subtle">
          Percorso guidato
        </div>
        <div className="text-[10px] tabular-nums text-ink-subtle">
          Step {stepIdx + 1} di {STEPS.length}
        </div>
      </div>
      <div
        className="mb-3 h-1 overflow-hidden rounded-full bg-[var(--color-surface)]"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="h-full rounded-full bg-[var(--color-brand)] transition-[width] duration-[var(--duration-slow)] ease-out"
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="flex gap-2 overflow-x-auto pb-1">
        {STEPS.map((s, i) => {
          const passed = i < stepIdx;
          const current = i === stepIdx;
          const navigable = passed; // future steps require validation
          const Tag = navigable ? 'button' : 'div';
          const Icon = iconForStep(s.id);
          return (
            <Tag
              key={s.id}
              aria-current={current ? 'step' : undefined}
              aria-label={`Step ${i + 1} di ${STEPS.length}: ${s.label}${
                passed ? ' (completato)' : current ? ' (corrente)' : ''
              }`}
              onClick={navigable ? () => onJump(s.id) : undefined}
              disabled={navigable ? false : undefined}
              className={cn(
                'inline-flex min-w-[8.25rem] items-center gap-2 rounded-lg border px-2.5 py-2 text-left transition-colors',
                current
                  ? 'border-[var(--color-brand)] bg-[var(--color-brand-soft)] text-ink shadow-sm'
                  : passed
                    ? 'border-[var(--color-success)]/25 bg-[var(--color-success)]/10 text-ink-muted'
                    : 'border-[var(--color-border)] bg-[var(--color-canvas-raised)] text-ink-subtle',
                navigable ? 'cursor-pointer hover:bg-[var(--color-surface)] focus-ring' : ''
              )}
            >
              <span
                className={cn(
                  'grid size-6 shrink-0 place-items-center rounded-md border text-[10px] font-semibold',
                  current
                    ? 'border-[var(--color-brand)] bg-[var(--color-brand)] text-white'
                    : passed
                      ? 'border-[var(--color-success)]/30 bg-[var(--color-success)]/15 text-[var(--color-success)]'
                      : 'border-[var(--color-border)] bg-[var(--color-surface)] text-ink-subtle'
                )}
              >
                {passed ? <CheckCircle2 size={13} /> : <Icon size={13} />}
              </span>
              <span className="min-w-0">
                <span
                  className={cn(
                    'block truncate text-[11.5px]',
                    current ? 'font-semibold text-ink' : 'font-medium'
                  )}
                >
                  {s.label}
                </span>
                <span className="block truncate text-[9.5px] text-ink-subtle">
                  {hintForStep(s.id)}
                </span>
              </span>
            </Tag>
          );
        })}
      </div>
    </nav>
  );
}

function iconForStep(step: Step) {
  switch (step) {
    case 'identity':
      return Building2;
    case 'vault':
      return Database;
    case 'branding':
      return Palette;
    case 'documents':
      return FileText;
    case 'provider':
      return KeyRound;
    default:
      return ShieldCheck;
  }
}

function hintForStep(step: Step): string {
  switch (step) {
    case 'identity':
      return 'Dominio';
    case 'vault':
      return 'Storage';
    case 'branding':
      return 'Look & feel';
    case 'documents':
      return 'PDF';
    case 'provider':
      return 'LLM';
    default:
      return 'Conferma';
  }
}
