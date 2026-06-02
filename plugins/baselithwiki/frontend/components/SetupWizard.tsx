import { zodResolver } from '@hookform/resolvers/zod';
import { AnimatePresence, motion } from 'framer-motion';
import { RefreshCw, Sparkles, X } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { useForm } from 'react-hook-form';
import { toast } from 'sonner';
import { IconButton } from './ui';
import {
  activateTenant,
  fetchScaffoldDefaults,
  fetchTenants,
  previewScaffold,
  type ScaffoldDefaults,
  type ScaffoldPlanResponse,
  type ScaffoldResultResponse,
  type TenantInfo,
} from '../lib/api';
import { cn } from '../lib/cn';
import { ease, duration } from '../lib/motion';
import { DocUploadList } from './upload/DocUploadList';
import { humanError, humanise } from './wizard/helpers';
import {
  buildScaffoldBody,
  DEFAULT_FORM,
  DRAFT_KEY,
  STEPS,
  wizardSchema,
  type Step,
  type WizardForm,
} from './wizard/schema';
import { useScaffoldApply } from './wizard/useScaffoldApply';
import { WizardBody } from './wizard/WizardBody';
import { WizardFooter } from './wizard/WizardFooter';
import { WizardHero } from './wizard/WizardHero';
import { WizardSidebar } from './wizard/WizardSidebar';
import { WizardStepper } from './wizard/WizardStepper';

interface Props {
  open: boolean;
  onClose: () => void;
  /** When true, the wizard is the only thing the user can interact with
   * (first-run mode). The close button is hidden. */
  blocking?: boolean;
  /** Visual variant.
   * - `modal` (default): centered card over a backdrop, dismissible.
   * - `screen`: full-viewport setup experience with branded hero.
   *   Use this for the first-run gate so the user never sees the
   *   chat/sidebar UI before a domain is active.
   */
  variant?: 'modal' | 'screen';
  /** Called after a successful scaffold apply, before showing the restart panel. */
  onScaffolded?: (result: ScaffoldResultResponse) => void;
}

export function SetupWizard({
  open,
  onClose,
  blocking = false,
  variant = 'modal',
  onScaffolded,
}: Props) {
  const [step, setStep] = useState<Step>('identity');
  const [defaults, setDefaults] = useState<ScaffoldDefaults | null>(null);
  const [tenants, setTenants] = useState<TenantInfo[]>([]);
  const [activeTenant, setActiveTenant] = useState<string | null>(null);
  const [plan, setPlan] = useState<ScaffoldPlanResponse | null>(null);
  const [planLoading, setPlanLoading] = useState(false);
  const [planError, setPlanError] = useState<string | null>(null);
  const [result, setResult] = useState<ScaffoldResultResponse | null>(null);
  const [showProvider, setShowProvider] = useState(false);
  const dialogRef = useRef<HTMLDivElement | null>(null);
  const stepBodyRef = useRef<HTMLDivElement | null>(null);
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [docFiles, setDocFiles] = useState<File[]>([]);

  // Auto-focus the first focusable input on step change for keyboard users.
  useEffect(() => {
    if (!stepBodyRef.current) return;
    const first = stepBodyRef.current.querySelector<HTMLElement>(
      'input:not([type="hidden"]):not([disabled]), select:not([disabled]), textarea:not([disabled]), button:not([disabled])'
    );
    // Defer to allow framer-motion mount to settle before focus.
    const id = window.setTimeout(() => first?.focus({ preventScroll: true }), 80);
    return () => window.clearTimeout(id);
  }, [step]);

  const {
    control,
    register,
    handleSubmit,
    watch,
    setValue,
    trigger,
    reset,
    formState: { errors, isValid },
  } = useForm<WizardForm>({
    resolver: zodResolver(wizardSchema),
    mode: 'onChange',
    defaultValues: DEFAULT_FORM,
  });

  const values = watch();

  const refresh = useCallback(async () => {
    try {
      const [d, t] = await Promise.all([fetchScaffoldDefaults(), fetchTenants(true)]);
      setDefaults(d);
      setTenants(t.tenants);
      setActiveTenant(t.active);
    } catch {
      // bootstrap failure surfaces via empty defaults/tenants in UI
    }
  }, []);

  // localStorage draft persistence (non-blocking only). First-run blocking
  // mode never persists — fresh installs deserve a clean slate.
  useEffect(() => {
    if (!open) return;
    setStep('identity');
    setPlan(null);
    setResult(null);
    setPlanError(null);
    let initial = DEFAULT_FORM;
    if (!blocking) {
      try {
        const raw = localStorage.getItem(DRAFT_KEY);
        if (raw) {
          const draft = JSON.parse(raw) as Partial<WizardForm>;
          initial = { ...DEFAULT_FORM, ...draft };
        }
      } catch {
        /* ignore corrupt draft */
      }
    }
    reset(initial);
    refresh();
  }, [open, blocking, refresh, reset]);

  // Persist form values to localStorage as the user types (non-blocking only).
  useEffect(() => {
    if (!open || blocking) return;
    try {
      // strip secrets before persisting — never write API keys to disk.
      const { provider_api_key: _, ...safe } = values;
      localStorage.setItem(DRAFT_KEY, JSON.stringify(safe));
    } catch {
      /* storage disabled */
    }
  }, [open, blocking, values]);

  // Keyboard shortcuts:
  // - Esc: close (unless blocking)
  // - Enter (outside textareas): advance to next step
  // - Cmd/Ctrl+Enter: submit on review step
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !blocking) {
        onClose();
        return;
      }
      const target = e.target as HTMLElement | null;
      const inMultiline = target?.tagName === 'TEXTAREA';
      const mod = e.metaKey || e.ctrlKey;
      if (e.key === 'Enter' && !inMultiline) {
        if (step === 'review' && mod) {
          e.preventDefault();
          void onApply();
        } else if (step !== 'review' && step !== 'done') {
          // forms shouldn't auto-submit GET-style; only advance steps.
          e.preventDefault();
          void goNext();
        }
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, blocking, step, onClose]);

  // auto-fill label from slug if user hasn't typed one
  useEffect(() => {
    if (!values.name) return;
    const current = values.label?.trim() ?? '';
    const previousAuto = humanise(values.name);
    if (current === '' || current === previousAuto.replace(/.$/, '')) {
      setValue('label', humanise(values.name), { shouldDirty: false });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [values.name]);

  const goReview = useCallback(async () => {
    const valid = await trigger();
    if (!valid) return;
    setPlanLoading(true);
    setPlanError(null);
    try {
      const p = await previewScaffold(buildScaffoldBody(watch()));
      setPlan(p);
      setStep('review');
    } catch (err) {
      setPlanError(humanError(err));
      toast.error(humanError(err));
    } finally {
      setPlanLoading(false);
    }
  }, [trigger, watch]);

  const scaffoldApply = useScaffoldApply({
    buildBody: () => buildScaffoldBody(watch()),
    themeBody: () => {
      const v = watch();
      const tb: { primary?: string; primary_hover?: string; accent?: string } = {};
      if (v.theme_primary) tb.primary = v.theme_primary;
      if (v.theme_primary_hover) tb.primary_hover = v.theme_primary_hover;
      if (v.theme_accent) tb.accent = v.theme_accent;
      return tb;
    },
    logoFile,
    docFiles,
    onScaffolded: (r) => {
      setResult(r);
      onScaffolded?.(r);
    },
  });

  const onApply = handleSubmit(async () => {
    const r = await scaffoldApply.apply();
    if (r) {
      setStep('done');
      refresh();
    }
  });

  const applyLoading = scaffoldApply.state.applying;

  const onSelectExisting = async (name: string) => {
    if (name === activeTenant) {
      toast.info(`«${name}» è già la wiki attiva.`);
      return;
    }
    try {
      const r = await activateTenant(name);
      if (r.written) {
        toast.success(`«${name}» selezionata. Verrà attivata al prossimo avvio.`);
        setActiveTenant(name);
      } else {
        toast.error('Non è stato possibile salvare la selezione. Riprova.');
      }
    } catch (err) {
      toast.error(humanError(err));
    }
  };

  const onForkSeed = (slug: string) => {
    setValue('from_seed', slug, { shouldDirty: true });
    // suggest a non-conflicting slug + label
    const suggestion = `${slug}_custom`;
    if (!values.name) setValue('name', suggestion, { shouldDirty: true });
    toast.info(`Duplicazione da «${slug}». Compila i restanti campi.`);
  };

  // step navigation helpers
  const canBack = step !== 'identity' && step !== 'done';
  const canNext =
    step === 'identity' ||
    step === 'vault' ||
    step === 'branding' ||
    step === 'documents' ||
    step === 'provider';

  const goNext = async () => {
    if (step === 'identity') {
      const ok = await trigger(['name', 'label', 'description', 'language']);
      if (ok) setStep('vault');
    } else if (step === 'vault') {
      const ok = await trigger(['vault_root', 'activate']);
      if (ok) setStep('branding');
    } else if (step === 'branding') {
      const ok = await trigger(['theme_primary', 'theme_primary_hover', 'theme_accent']);
      if (ok) setStep('documents');
    } else if (step === 'documents') {
      setStep('provider');
    } else if (step === 'provider') {
      await goReview();
    }
  };

  const goBack = () => {
    if (step === 'vault') setStep('identity');
    else if (step === 'branding') setStep('vault');
    else if (step === 'documents') setStep('branding');
    else if (step === 'provider') setStep('documents');
    else if (step === 'review') setStep('provider');
  };

  const isScreen = variant === 'screen';
  const stepIdx =
    step === 'done'
      ? STEPS.length - 1
      : Math.max(
          0,
          STEPS.findIndex((s) => s.id === step)
        );
  const workflowComplete = step === 'done';
  const progressPct = workflowComplete ? 100 : Math.round(((stepIdx + 1) / STEPS.length) * 100);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.12 }}
          onClick={() => !blocking && onClose()}
          className={cn(
            'fixed inset-0 z-50',
            isScreen
              ? 'bg-canvas wizard-screen-bg overflow-y-auto px-3 py-4 sm:px-6 sm:py-6'
              : 'bg-black/50 backdrop-blur-sm grid place-items-center'
          )}
          role="dialog"
          aria-modal="true"
          aria-label="setup wizard nuova wiki"
        >
          {isScreen && <WizardHero progressPct={progressPct} onRefresh={refresh} />}

          <motion.div
            ref={dialogRef}
            initial={{ opacity: 0, scale: 0.96, y: 6 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 6 }}
            transition={{ duration: 0.14 }}
            onClick={(e) => e.stopPropagation()}
            className={cn(
              'relative z-10 w-full overflow-hidden border border-[var(--color-border)] bg-[var(--color-canvas-raised)] shadow-2xl',
              isScreen
                ? 'mx-auto flex h-[calc(100vh-148px)] max-h-[760px] max-w-6xl rounded-lg'
                : 'mx-4 flex max-h-[90vh] max-w-4xl flex-col rounded-lg'
            )}
          >
            {isScreen && (
              <WizardSidebar
                values={values}
                stepIdx={stepIdx}
                progressPct={progressPct}
                workflowComplete={workflowComplete}
              />
            )}

            <section className="flex min-w-0 flex-1 flex-col">
              <header className="flex items-center justify-between border-b border-[var(--color-border)] px-4 py-3 sm:px-5">
                <div className="inline-flex min-w-0 items-center gap-2">
                  <Sparkles size={14} className="shrink-0 text-[var(--color-brand)]" aria-hidden />
                  <span className="truncate text-sm font-semibold text-ink">
                    Configurazione wiki
                  </span>
                  <span className="hidden text-[10px] text-ink-subtle sm:inline">
                    creazione guidata
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  {!isScreen && (
                    <IconButton
                      icon={RefreshCw}
                      aria-label="aggiorna elenco wiki"
                      size="sm"
                      onClick={refresh}
                    />
                  )}
                  {!blocking && (
                    <IconButton icon={X} aria-label="chiudi" size="sm" onClick={onClose} />
                  )}
                </div>
              </header>

              {step !== 'done' && (
                <div className={cn(isScreen && 'lg:hidden')}>
                  <WizardStepper step={step} onJump={setStep} />
                </div>
              )}

              <div ref={stepBodyRef} className="flex-1 overflow-y-auto">
                <AnimatePresence mode="wait" initial={false}>
                  <motion.div
                    key={step}
                    initial={{ opacity: 0, x: 8 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -6 }}
                    transition={{ duration: duration.base, ease: ease.outQuart }}
                  >
                    <WizardBody
                      step={step}
                      values={values}
                      register={register}
                      control={control}
                      errors={errors}
                      setValue={setValue}
                      defaults={defaults}
                      tenants={tenants}
                      activeTenant={activeTenant}
                      onSelectExisting={onSelectExisting}
                      onForkSeed={onForkSeed}
                      logoFile={logoFile}
                      setLogoFile={setLogoFile}
                      docFiles={docFiles}
                      setDocFiles={setDocFiles}
                      showProvider={showProvider}
                      setShowProvider={setShowProvider}
                      plan={plan}
                      planLoading={planLoading}
                      planError={planError}
                      result={result}
                      onClose={onClose}
                    />
                  </motion.div>
                </AnimatePresence>
              </div>

              {step === 'review' && scaffoldApply.state.phase === 'docs' && (
                <div className="px-5 pt-3">
                  <DocUploadList docs={scaffoldApply.state.docs} />
                </div>
              )}

              {step !== 'done' && (
                <WizardFooter
                  step={step}
                  canBack={canBack}
                  canNext={canNext}
                  isValid={isValid}
                  applyLoading={applyLoading}
                  planLoading={planLoading}
                  hasPlan={!!plan}
                  applyPhase={scaffoldApply.state.phase}
                  onBack={goBack}
                  onNext={goNext}
                  onApply={onApply}
                />
              )}
            </section>
          </motion.div>

          {isScreen && (
            <motion.footer
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.2, delay: 0.15 }}
              className="mx-auto mt-6 max-w-md text-center text-[10.5px] text-ink-subtle"
            >
              <details className="inline-block text-left">
                <summary className="cursor-pointer text-ink-muted hover:text-ink">
                  Preferisci configurare da terminale?
                </summary>
                <pre className="mt-2 inline-block rounded bg-[var(--color-surface)] px-2 py-1 font-mono text-[10.5px] text-ink-muted">
                  python -m llm_wiki init --domain &lt;name&gt;
                </pre>
              </details>
            </motion.footer>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// quick utility re-export so the wizard's caller can access it without
// re-importing react-hook-form types
export type { ScaffoldResultResponse };
