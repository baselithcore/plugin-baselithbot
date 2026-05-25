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
import { STEPS, type Step, type WizardForm } from './schema';

interface Props {
  values: WizardForm;
  stepIdx: number;
  progressPct: number;
  workflowComplete: boolean;
}

/**
 * Left rail of the screen-variant SetupWizard. Renders the brand chip,
 * progress bar, ordered step list and the "review required" reassurance card.
 */
export function WizardSidebar({ values, stepIdx, progressPct, workflowComplete }: Props) {
  return (
    <aside className="hidden w-72 shrink-0 flex-col border-r border-[var(--color-border)] bg-[var(--color-surface)]/45 p-5 lg:flex">
      <div className="flex items-center gap-2">
        <div className="grid size-9 place-items-center rounded-lg bg-[var(--color-brand)] text-white shadow-sm">
          <Building2 size={16} />
        </div>
        <div className="min-w-0">
          <div className="text-sm font-semibold text-ink">Nuova wiki</div>
          <div className="truncate text-[10.5px] text-ink-subtle">
            {values.label || values.name || 'In allestimento'}
          </div>
        </div>
      </div>

      <div className="mt-6">
        <div className="mb-2 flex items-center justify-between text-[10px] font-semibold uppercase text-ink-subtle">
          <span>Avanzamento</span>
          <span>
            {stepIdx + 1}/{STEPS.length}
          </span>
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-[var(--color-border)]">
          <div
            className="h-full rounded-full bg-[var(--color-brand)] transition-all"
            style={{ width: `${progressPct}%` }}
          />
        </div>
      </div>

      <ol className="mt-5 space-y-2">
        {STEPS.map((s, i) => {
          const passed = workflowComplete || i < stepIdx;
          const current = !workflowComplete && i === stepIdx;
          const Icon = sideIconForStep(s.id);
          return (
            <li key={s.id} className="flex items-center gap-3">
              <span
                className={cn(
                  'grid size-7 shrink-0 place-items-center rounded-lg border text-[10px]',
                  current
                    ? 'border-[var(--color-brand)] bg-[var(--color-brand)] text-white'
                    : passed
                      ? 'border-[var(--color-success)]/30 bg-[var(--color-success)]/10 text-[var(--color-success)]'
                      : 'border-[var(--color-border)] bg-[var(--color-canvas-raised)] text-ink-subtle'
                )}
              >
                {passed ? <CheckCircle2 size={14} /> : <Icon size={14} />}
              </span>
              <div className="min-w-0">
                <div
                  className={cn(
                    'text-[12px]',
                    current ? 'font-semibold text-ink' : 'font-medium text-ink-muted'
                  )}
                >
                  {s.label}
                </div>
                <div className="truncate text-[10px] text-ink-subtle">{sideHintForStep(s.id)}</div>
              </div>
            </li>
          );
        })}
      </ol>

      <div className="mt-auto rounded-lg border border-[var(--color-border)] bg-[var(--color-canvas-raised)] p-3 shadow-sm">
        <div className="text-[11px] font-semibold text-ink">Revisione obbligatoria</div>
        <p className="mt-1 text-[10.5px] leading-relaxed text-ink-muted">
          Vedrai un riepilogo completo prima di confermare. Nessuna modifica viene applicata senza
          la tua conferma esplicita.
        </p>
      </div>
    </aside>
  );
}

function sideIconForStep(step: Step) {
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

function sideHintForStep(step: Step): string {
  switch (step) {
    case 'identity':
      return 'Nome, lingua, seed';
    case 'vault':
      return 'Storage locale';
    case 'branding':
      return 'Logo e palette';
    case 'documents':
      return 'PDF iniziali';
    case 'provider':
      return 'LLM opzionale';
    default:
      return 'Diff e conferma';
  }
}
