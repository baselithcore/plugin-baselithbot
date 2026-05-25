import { ArrowLeft, ArrowRight, Sparkles } from 'lucide-react';
import { Button } from '../ui';
import { STEPS, type Step } from './schema';
import type { ApplyPhase } from './useScaffoldApply';

interface WizardFooterProps {
  step: Step;
  canBack: boolean;
  canNext: boolean;
  isValid: boolean;
  applyLoading: boolean;
  planLoading: boolean;
  hasPlan: boolean;
  applyPhase: ApplyPhase;
  onBack: () => void;
  onNext: () => void;
  onApply: () => void;
}

export function WizardFooter({
  step,
  canBack,
  canNext,
  isValid,
  applyLoading,
  planLoading,
  hasPlan,
  applyPhase,
  onBack,
  onNext,
  onApply,
}: WizardFooterProps) {
  const stepIdx = STEPS.findIndex((s) => s.id === step);

  return (
    <footer className="border-t border-[var(--color-border)] bg-[var(--color-canvas-raised)] px-4 py-3 sm:px-5">
      <div className="flex items-center justify-between gap-3">
        <Button
          variant="ghost"
          leadingIcon={ArrowLeft}
          disabled={!canBack || applyLoading}
          onClick={onBack}
        >
          Indietro
        </Button>
        <div className="hidden min-w-0 flex-1 text-center sm:block">
          <div className="text-[11px] font-medium text-ink-muted">{footerTitle(step)}</div>
          <div className="text-[10px] text-ink-subtle">
            {stepIdx + 1}/{STEPS.length} · {footerHint(step)}
          </div>
        </div>
        {step === 'review' ? (
          <Button
            variant="primary"
            leadingIcon={Sparkles}
            disabled={!hasPlan || !isValid}
            loading={applyLoading}
            onClick={onApply}
          >
            {applyLoading ? phaseLabel(applyPhase) : 'Crea wiki'}
          </Button>
        ) : (
          <Button
            variant="primary"
            trailingIcon={ArrowRight}
            disabled={canNext === false && step !== 'provider'}
            loading={planLoading}
            onClick={onNext}
          >
            {step === 'provider' ? 'Rivedi e crea' : 'Avanti'}
          </Button>
        )}
      </div>
    </footer>
  );
}

function phaseLabel(p: ApplyPhase): string {
  switch (p) {
    case 'scaffold':
      return 'Configurazione…';
    case 'theme':
      return 'Salvo tema…';
    case 'logo':
      return 'Carico logo…';
    case 'docs':
      return 'Carico documenti…';
    case 'done':
      return 'Completato';
    default:
      return 'In corso…';
  }
}

function footerTitle(step: Step): string {
  switch (step) {
    case 'identity':
      return 'Definisci identità del dominio';
    case 'vault':
      return 'Scegli dove salvare la knowledge base';
    case 'branding':
      return "Personalizza l'aspetto";
    case 'documents':
      return 'Aggiungi i primi documenti';
    case 'provider':
      return 'Configura il modello (opzionale)';
    default:
      return 'Controlla prima di confermare';
  }
}

function footerHint(step: Step): string {
  switch (step) {
    case 'identity':
      return 'nome, lingua, esempio di partenza';
    case 'vault':
      return 'cartella locale per documenti e pagine';
    case 'branding':
      return 'logo e colori opzionali';
    case 'documents':
      return 'puoi caricarli anche dopo';
    case 'provider':
      return 'le chiavi restano in locale';
    default:
      return 'tutto reversibile prima di confermare';
  }
}
