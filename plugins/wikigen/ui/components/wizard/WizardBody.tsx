import type { UseFormRegister, UseFormSetValue } from 'react-hook-form';
import type {
  ScaffoldDefaults,
  ScaffoldPlanResponse,
  ScaffoldResultResponse,
  TenantInfo,
} from '../../lib/api';
import { IdentityStepSkeleton } from './atoms';
import { DonePanel } from './DonePanel';
import type { Step, WizardForm } from './schema';
import { BrandingStep } from './steps/BrandingStep';
import { DocumentsStep } from './steps/DocumentsStep';
import { IdentityStep } from './steps/IdentityStep';
import { ProviderStep } from './steps/ProviderStep';
import { ReviewStep } from './steps/ReviewStep';
import { VaultStep } from './steps/VaultStep';

interface WizardBodyProps {
  step: Step;
  values: WizardForm;
  register: UseFormRegister<WizardForm>;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  control: any;
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  errors: any;
  setValue: UseFormSetValue<WizardForm>;
  defaults: ScaffoldDefaults | null;
  tenants: TenantInfo[];
  activeTenant: string | null;
  onSelectExisting: (name: string) => void;
  onForkSeed: (slug: string) => void;
  logoFile: File | null;
  setLogoFile: (f: File | null) => void;
  docFiles: File[];
  setDocFiles: (f: File[]) => void;
  showProvider: boolean;
  setShowProvider: (v: boolean) => void;
  plan: ScaffoldPlanResponse | null;
  planLoading: boolean;
  planError: string | null;
  result: ScaffoldResultResponse | null;
  onClose: () => void;
}

/**
 * Renders the active wizard step. Splits the conditional body out of
 * SetupWizard.tsx so the orchestrator focuses on state + flow.
 */
export function WizardBody(p: WizardBodyProps) {
  const { step } = p;

  if (step === 'identity') {
    if (p.defaults === null) return <IdentityStepSkeleton />;
    return (
      <IdentityStep
        register={p.register}
        control={p.control}
        errors={p.errors}
        defaults={p.defaults}
        tenants={p.tenants}
        activeTenant={p.activeTenant}
        onSelectExisting={p.onSelectExisting}
        onForkSeed={p.onForkSeed}
        fromSeed={p.values.from_seed ?? ''}
        setFromSeed={(slug) => p.setValue('from_seed', slug, { shouldDirty: true })}
      />
    );
  }
  if (step === 'vault') {
    return <VaultStep register={p.register} errors={p.errors} values={p.values} />;
  }
  if (step === 'branding') {
    return (
      <BrandingStep
        register={p.register}
        errors={p.errors}
        values={p.values}
        setValue={p.setValue}
        logoFile={p.logoFile}
        setLogoFile={p.setLogoFile}
      />
    );
  }
  if (step === 'documents') {
    return <DocumentsStep docFiles={p.docFiles} setDocFiles={p.setDocFiles} />;
  }
  if (step === 'provider') {
    return (
      <ProviderStep
        register={p.register}
        control={p.control}
        errors={p.errors}
        values={p.values}
        setValue={p.setValue}
        showProvider={p.showProvider}
        setShowProvider={p.setShowProvider}
      />
    );
  }
  if (step === 'review') {
    return (
      <ReviewStep
        plan={p.plan}
        planLoading={p.planLoading}
        planError={p.planError}
        register={p.register}
        synthesizePrompts={p.values.synthesize_prompts}
        fromSeed={p.values.from_seed ?? ''}
      />
    );
  }
  if (step === 'done' && p.result) {
    return <DonePanel result={p.result} expectedDocs={p.docFiles.length} onClose={p.onClose} />;
  }
  return null;
}
