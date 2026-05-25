/**
 * SuperuserWizard — first-boot superuser creation flow (multi-step).
 *
 * Sostituisce ``BootstrapGate`` come UX di primo avvio. Mostrato da
 * App.tsx PRIMA di auth/setup quando ``GET /auth/bootstrap/status``
 * ritorna ``needs_bootstrap=true``. Endpoint backend resta loopback-only
 * durante questo stato (gate in :mod:`api/routers/auth/bootstrap.py`).
 *
 * Allineato visivamente al ``SetupWizard`` (variant screen) per
 * coerenza: hero brandizzata, sidebar avanzamento, stepper, footer
 * back/next, transizioni framer-motion. Stessi token motion/colori
 * (``ease``/``duration``, var CSS ``--color-brand``).
 *
 * Steps:
 *  1. **identity** — email, display name, tenant slug opzionale
 *  2. **security** — password + conferma + meter di robustezza
 *  3. **review**   — riepilogo + conferma esplicita
 *
 * Best practice 2026:
 *  - Validazione client speculare a backend (Pydantic ≥12 char).
 *  - Toggle show/hide password (ARIA-labeled).
 *  - autocomplete=new-password (no leak in password managers).
 *  - Nessuna pre-compilazione, nessun suggerimento password.
 *  - Strength meter live, no submit con password debole.
 *  - Cmd/Ctrl+Enter su review → conferma, Esc disabilitato (blocking).
 */

import { AnimatePresence, motion } from 'framer-motion';
import {
  ArrowLeft,
  ArrowRight,
  Building2,
  CheckCircle2,
  Eye,
  EyeOff,
  KeyRound,
  Mail,
  ShieldCheck,
  Sparkles,
  User,
} from 'lucide-react';
import {
  type ChangeEvent,
  type ReactNode,
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from 'react';

import { useAuth } from '../contexts/AuthContext';
import * as authApi from '../lib/api/auth';
import { ApiError } from '../lib/api/client';
import { cn } from '../lib/cn';
import { duration, ease } from '../lib/motion';
import { Button } from './ui/Button';

const PASSWORD_MIN = 12;

type Step = 'identity' | 'security' | 'review';

interface StepMeta {
  id: Step;
  label: string;
  hint: string;
  icon: typeof Building2;
}

const STEPS: StepMeta[] = [
  { id: 'identity', label: 'Identità', hint: 'Email e profilo', icon: User },
  { id: 'security', label: 'Sicurezza', hint: 'Password ≥12 char', icon: KeyRound },
  { id: 'review', label: 'Conferma', hint: 'Crea superuser', icon: ShieldCheck },
];

interface Props {
  /** Chiamato quando bootstrap completato (o non necessario). */
  onComplete: () => void;
}

export function SuperuserWizard({ onComplete }: Props) {
  const [checking, setChecking] = useState(true);
  const [needs, setNeeds] = useState(false);
  const [step, setStep] = useState<Step>('identity');
  const [email, setEmail] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [tenantSlug, setTenantSlug] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const stepBodyRef = useRef<HTMLDivElement | null>(null);
  const { refreshUser } = useAuth();

  // Status check loopback. fail-open in caso di errore (DB irraggiungibile o
  // auth disabilitato) → cede al normale auth gate downstream.
  useEffect(() => {
    const ac = new AbortController();
    authApi
      .bootstrapStatus(ac.signal)
      .then((s) => {
        setNeeds(s.needs_bootstrap);
        setChecking(false);
        if (!s.needs_bootstrap) onComplete();
      })
      .catch(() => {
        setChecking(false);
        setNeeds(false);
        onComplete();
      });
    return () => ac.abort();
  }, [onComplete]);

  // Auto-focus primo input al cambio step (keyboard users).
  useEffect(() => {
    if (!needs) return;
    if (!stepBodyRef.current) return;
    const first = stepBodyRef.current.querySelector<HTMLElement>(
      'input:not([type="hidden"]):not([disabled])'
    );
    const id = window.setTimeout(() => first?.focus({ preventScroll: true }), 80);
    return () => window.clearTimeout(id);
  }, [step, needs]);

  // Email validation speculare al backend regex.
  const emailValid = /^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/.test(email.trim());
  const passwordLong = password.length >= PASSWORD_MIN;
  const passwordsMatch = password.length > 0 && password === confirm;
  const passwordScore = useMemo(
    () =>
      [
        password.length >= PASSWORD_MIN,
        /[A-Za-zÀ-ÿ]/.test(password),
        /[0-9]/.test(password),
        /[^A-Za-zÀ-ÿ0-9]/.test(password),
      ].filter(Boolean).length,
    [password]
  );

  const identityValid = emailValid;
  const securityValid = passwordLong && passwordsMatch && passwordScore >= 2;
  const allValid = identityValid && securityValid;

  const stepIdx = STEPS.findIndex((s) => s.id === step);
  const progressPct = Math.round(((stepIdx + 1) / STEPS.length) * 100);

  const goNext = useCallback(() => {
    setError(null);
    if (step === 'identity') {
      if (!identityValid) {
        setError('Inserisci un indirizzo email valido.');
        return;
      }
      setStep('security');
    } else if (step === 'security') {
      if (!securityValid) {
        setError(
          passwordLong
            ? passwordsMatch
              ? 'La password è troppo debole. Aggiungi numeri o simboli.'
              : 'Le password non coincidono.'
            : `Password minimo ${PASSWORD_MIN} caratteri.`
        );
        return;
      }
      setStep('review');
    }
  }, [step, identityValid, securityValid, passwordLong, passwordsMatch]);

  const goBack = useCallback(() => {
    setError(null);
    if (step === 'security') setStep('identity');
    else if (step === 'review') setStep('security');
  }, [step]);

  const submit = useCallback(async () => {
    if (!allValid) {
      setError('Completa i passi precedenti prima di confermare.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await authApi.bootstrap({
        email: email.trim().toLowerCase(),
        password,
        display_name: displayName.trim(),
        tenant_slug: tenantSlug.trim() || undefined,
      });
      // Cookie refresh emesso server-side, AuthContext non ha visto il login
      // sincrono: forziamo refresh user.
      await refreshUser();
      onComplete();
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 403) {
          setError(
            'Bootstrap non consentito da questa origine. Apri la UI da localhost durante il primo setup.'
          );
        } else if (err.status === 400) {
          setError(err.message || 'Validazione fallita.');
        } else if (err.status === 503) {
          setError('Database non disponibile. Riprova fra qualche secondo.');
        } else {
          setError(err.message || `Errore (${err.status}).`);
        }
      } else {
        setError(err instanceof Error ? err.message : 'Errore imprevisto.');
      }
    } finally {
      setBusy(false);
    }
  }, [allValid, email, password, displayName, tenantSlug, refreshUser, onComplete]);

  // Keyboard: Enter → next/submit (outside textarea), Cmd/Ctrl+Enter su review → submit.
  useEffect(() => {
    if (!needs) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Enter') return;
      const t = e.target as HTMLElement | null;
      if (t?.tagName === 'TEXTAREA') return;
      const mod = e.metaKey || e.ctrlKey;
      if (step === 'review' && mod) {
        e.preventDefault();
        void submit();
      } else if (step !== 'review') {
        e.preventDefault();
        goNext();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [needs, step, submit, goNext]);

  if (checking) {
    return <div className="h-screen w-screen bg-canvas" aria-hidden="true" />;
  }
  if (!needs) {
    return null;
  }

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.12 }}
        className="wizard-screen-bg fixed inset-0 z-50 overflow-y-auto bg-canvas px-3 py-4 sm:px-6 sm:py-6"
        role="dialog"
        aria-modal="true"
        aria-label="setup superuser iniziale"
      >
        <SuperuserHero progressPct={progressPct} />

        <motion.div
          initial={{ opacity: 0, scale: 0.96, y: 6 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.96, y: 6 }}
          transition={{ duration: 0.14 }}
          className="relative z-10 mx-auto flex h-[calc(100vh-148px)] max-h-[760px] w-full max-w-6xl overflow-hidden rounded-lg border border-[var(--color-border)] bg-[var(--color-canvas-raised)] shadow-2xl"
        >
          <SuperuserSidebar
            stepIdx={stepIdx}
            progressPct={progressPct}
            email={email}
            displayName={displayName}
          />

          <section className="flex min-w-0 flex-1 flex-col">
            <header className="flex items-center justify-between border-b border-[var(--color-border)] px-4 py-3 sm:px-5">
              <div className="inline-flex min-w-0 items-center gap-2">
                <Sparkles
                  size={14}
                  className="shrink-0 text-[var(--color-brand)]"
                  aria-hidden
                />
                <span className="truncate text-sm font-semibold text-ink">
                  Crea il primo superuser
                </span>
                <span className="hidden text-[10px] text-ink-subtle sm:inline">
                  one-time, loopback-only
                </span>
              </div>
            </header>

            <div className="lg:hidden">
              <SuperuserStepper step={step} />
            </div>

            <div ref={stepBodyRef} className="flex-1 overflow-y-auto">
              <AnimatePresence mode="wait" initial={false}>
                <motion.div
                  key={step}
                  initial={{ opacity: 0, x: 8 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -6 }}
                  transition={{ duration: duration.base, ease: ease.outQuart }}
                  className="px-4 py-5 sm:px-7 sm:py-7"
                >
                  {step === 'identity' && (
                    <IdentityStep
                      email={email}
                      setEmail={setEmail}
                      displayName={displayName}
                      setDisplayName={setDisplayName}
                      tenantSlug={tenantSlug}
                      setTenantSlug={setTenantSlug}
                      emailValid={emailValid}
                    />
                  )}
                  {step === 'security' && (
                    <SecurityStep
                      password={password}
                      setPassword={setPassword}
                      confirm={confirm}
                      setConfirm={setConfirm}
                      showPw={showPw}
                      onToggleShow={() => setShowPw((v) => !v)}
                      score={passwordScore}
                      tooShort={password.length > 0 && !passwordLong}
                      mismatch={confirm.length > 0 && !passwordsMatch}
                    />
                  )}
                  {step === 'review' && (
                    <ReviewStep
                      email={email}
                      displayName={displayName}
                      tenantSlug={tenantSlug}
                      score={passwordScore}
                    />
                  )}
                </motion.div>
              </AnimatePresence>
            </div>

            {error && (
              <div className="px-4 pb-2 sm:px-7">
                <p
                  role="alert"
                  className="rounded border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/10 px-3 py-2 text-xs text-[var(--color-danger)]"
                >
                  {error}
                </p>
              </div>
            )}

            <SuperuserFooter
              step={step}
              busy={busy}
              canNext={step === 'identity' ? identityValid : securityValid}
              hasAll={allValid}
              onBack={goBack}
              onNext={goNext}
              onSubmit={submit}
            />
          </section>
        </motion.div>

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
              wiki-wl create-superuser
            </pre>
          </details>
        </motion.footer>
      </motion.div>
    </AnimatePresence>
  );
}

// ──────────────────────────────────────────────────────────────────────────
// Sub-components
// ──────────────────────────────────────────────────────────────────────────

function SuperuserHero({ progressPct }: { progressPct: number }) {
  return (
    <motion.header
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18 }}
      className="relative z-10 mx-auto mb-4 flex w-full max-w-6xl items-center justify-between gap-4"
    >
      <div className="min-w-0">
        <div className="inline-flex items-center gap-2 rounded-full border border-[var(--color-border)] bg-[var(--color-canvas-raised)] px-3 py-1 text-[10px] font-semibold uppercase text-ink-muted shadow-sm">
          <ShieldCheck size={11} className="text-[var(--color-brand)]" />
          Inizializzazione enterprise
        </div>
        <h1 className="mt-2 text-2xl font-semibold text-ink sm:text-3xl">
          Crea il primo amministratore
        </h1>
        <p className="mt-1 max-w-2xl text-[12.5px] leading-relaxed text-ink-muted">
          Nessun account configurato. Questo passaggio è disponibile una sola volta dal browser
          locale e crea il superuser iniziale per il workspace.
        </p>
      </div>
      <div className="hidden shrink-0 items-center gap-2 lg:flex">
        <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-canvas-raised)] px-3 py-2 shadow-sm">
          <div className="text-[10px] uppercase text-ink-subtle">Progresso</div>
          <div className="mt-0.5 text-sm font-semibold tabular-nums text-ink">{progressPct}%</div>
        </div>
      </div>
    </motion.header>
  );
}

function SuperuserSidebar({
  stepIdx,
  progressPct,
  email,
  displayName,
}: {
  stepIdx: number;
  progressPct: number;
  email: string;
  displayName: string;
}) {
  return (
    <aside className="hidden w-72 shrink-0 flex-col border-r border-[var(--color-border)] bg-[var(--color-surface)]/45 p-5 lg:flex">
      <div className="flex items-center gap-2">
        <div className="grid size-9 place-items-center rounded-lg bg-[var(--color-brand)] text-white shadow-sm">
          <ShieldCheck size={16} />
        </div>
        <div className="min-w-0">
          <div className="text-sm font-semibold text-ink">Superuser iniziale</div>
          <div className="truncate text-[10.5px] text-ink-subtle">
            {displayName || email || 'In configurazione'}
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
          const passed = i < stepIdx;
          const current = i === stepIdx;
          const Icon = s.icon;
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
                <div className="truncate text-[10px] text-ink-subtle">{s.hint}</div>
              </div>
            </li>
          );
        })}
      </ol>

      <div className="mt-auto rounded-lg border border-[var(--color-border)] bg-[var(--color-canvas-raised)] p-3 shadow-sm">
        <div className="text-[11px] font-semibold text-ink">Loopback obbligatorio</div>
        <p className="mt-1 text-[10.5px] leading-relaxed text-ink-muted">
          Questa schermata accetta richieste solo da localhost. Per setup remoti usa la CLI
          (<code className="font-mono">wiki-wl create-superuser</code>).
        </p>
      </div>
    </aside>
  );
}

function SuperuserStepper({ step }: { step: Step }) {
  const stepIdx = STEPS.findIndex((s) => s.id === step);
  const pct = Math.round(((stepIdx + 1) / STEPS.length) * 100);

  return (
    <nav
      className="border-b border-[var(--color-border)] bg-[var(--color-canvas-raised)] px-4 py-3 sm:px-5"
      aria-label="progresso wizard superuser"
    >
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="text-[10px] font-semibold uppercase text-ink-subtle">Percorso guidato</div>
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
          const Icon = s.icon;
          return (
            <div
              key={s.id}
              aria-current={current ? 'step' : undefined}
              className={cn(
                'inline-flex min-w-[8.25rem] items-center gap-2 rounded-lg border px-2.5 py-2 text-left',
                current
                  ? 'border-[var(--color-brand)] bg-[var(--color-brand-soft)] text-ink shadow-sm'
                  : passed
                    ? 'border-[var(--color-success)]/25 bg-[var(--color-success)]/10 text-ink-muted'
                    : 'border-[var(--color-border)] bg-[var(--color-canvas-raised)] text-ink-subtle'
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
                <span className="block truncate text-[9.5px] text-ink-subtle">{s.hint}</span>
              </span>
            </div>
          );
        })}
      </div>
    </nav>
  );
}

function SuperuserFooter({
  step,
  busy,
  canNext,
  hasAll,
  onBack,
  onNext,
  onSubmit,
}: {
  step: Step;
  busy: boolean;
  canNext: boolean;
  hasAll: boolean;
  onBack: () => void;
  onNext: () => void;
  onSubmit: () => void;
}) {
  const stepIdx = STEPS.findIndex((s) => s.id === step);
  return (
    <footer className="border-t border-[var(--color-border)] bg-[var(--color-canvas-raised)] px-4 py-3 sm:px-5">
      <div className="flex items-center justify-between gap-3">
        <Button
          variant="ghost"
          leadingIcon={ArrowLeft}
          disabled={step === 'identity' || busy}
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
            disabled={!hasAll}
            loading={busy}
            onClick={onSubmit}
          >
            {busy ? 'Creazione…' : 'Crea superuser'}
          </Button>
        ) : (
          <Button
            variant="primary"
            trailingIcon={ArrowRight}
            disabled={!canNext || busy}
            onClick={onNext}
          >
            Avanti
          </Button>
        )}
      </div>
    </footer>
  );
}

function footerTitle(step: Step): string {
  switch (step) {
    case 'identity':
      return "Definisci l'identità dell'amministratore";
    case 'security':
      return 'Imposta una password forte';
    default:
      return 'Conferma e crea il superuser';
  }
}

function footerHint(step: Step): string {
  switch (step) {
    case 'identity':
      return 'email, nome visualizzato, tenant';
    case 'security':
      return `min ${PASSWORD_MIN} char, no leak`;
    default:
      return 'azione irreversibile finché esiste un superuser';
  }
}

// ──────────────────────────────────────────────────────────────────────────
// Step bodies
// ──────────────────────────────────────────────────────────────────────────

function IdentityStep({
  email,
  setEmail,
  displayName,
  setDisplayName,
  tenantSlug,
  setTenantSlug,
  emailValid,
}: {
  email: string;
  setEmail: (v: string) => void;
  displayName: string;
  setDisplayName: (v: string) => void;
  tenantSlug: string;
  setTenantSlug: (v: string) => void;
  emailValid: boolean;
}) {
  const emailId = useId();
  const nameId = useId();
  const tenantId = useId();
  return (
    <div className="mx-auto flex max-w-xl flex-col gap-4">
      <StepHeading
        title="Identità del superuser"
        body="Le credenziali verranno usate per accedere al pannello di amministrazione. Email e password resteranno modificabili dopo il primo accesso."
      />
      <FormField
        id={emailId}
        label="Email"
        icon={Mail}
        value={email}
        onChange={setEmail}
        type="email"
        autoComplete="username"
        placeholder="admin@example.com"
        required
        error={email.length > 0 && !emailValid ? 'Indirizzo email non valido.' : undefined}
      />
      <FormField
        id={nameId}
        label="Nome visualizzato"
        icon={User}
        value={displayName}
        onChange={setDisplayName}
        type="text"
        autoComplete="name"
        placeholder="Admin"
        hint="Opzionale — derivato dall'email se vuoto."
      />
      <FormField
        id={tenantId}
        label="Slug tenant"
        icon={Building2}
        value={tenantSlug}
        onChange={setTenantSlug}
        type="text"
        autoComplete="off"
        placeholder="(auto da email)"
        hint="Identificatore del workspace. Lettere minuscole e trattini."
      />
    </div>
  );
}

function SecurityStep({
  password,
  setPassword,
  confirm,
  setConfirm,
  showPw,
  onToggleShow,
  score,
  tooShort,
  mismatch,
}: {
  password: string;
  setPassword: (v: string) => void;
  confirm: string;
  setConfirm: (v: string) => void;
  showPw: boolean;
  onToggleShow: () => void;
  score: number;
  tooShort: boolean;
  mismatch: boolean;
}) {
  const pwId = useId();
  const confirmId = useId();
  const strengthLabel =
    score >= 4 ? 'Forte' : score === 3 ? 'Buona' : score === 2 ? 'Sufficiente' : 'Debole';

  return (
    <div className="mx-auto flex max-w-xl flex-col gap-4">
      <StepHeading
        title="Imposta la password"
        body={`Minimo ${PASSWORD_MIN} caratteri. Combina lettere, numeri e simboli per aumentare la robustezza. Non sarà mai mostrata né registrata in chiaro.`}
      />
      <PasswordField
        id={pwId}
        label={`Password (min ${PASSWORD_MIN} caratteri)`}
        value={password}
        onChange={setPassword}
        show={showPw}
        onToggleShow={onToggleShow}
        error={tooShort ? `Servono almeno ${PASSWORD_MIN} caratteri.` : undefined}
      />
      <StrengthMeter score={score} label={strengthLabel} />
      <PasswordField
        id={confirmId}
        label="Conferma password"
        value={confirm}
        onChange={setConfirm}
        show={showPw}
        onToggleShow={onToggleShow}
        error={mismatch ? 'Le password non coincidono.' : undefined}
      />
    </div>
  );
}

function ReviewStep({
  email,
  displayName,
  tenantSlug,
  score,
}: {
  email: string;
  displayName: string;
  tenantSlug: string;
  score: number;
}) {
  const tenantPreview =
    tenantSlug.trim() ||
    email
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9-]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 50) ||
    'admin';
  return (
    <div className="mx-auto flex max-w-xl flex-col gap-4">
      <StepHeading
        title="Conferma e crea"
        body="Verifica i dati. Dopo la conferma verrai loggato automaticamente e l'endpoint di bootstrap sarà disabilitato (gli ulteriori superuser si gestiscono dall'UI admin)."
      />
      <dl className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <ReviewRow label="Email" value={email.trim().toLowerCase()} />
        <ReviewRow
          label="Nome visualizzato"
          value={displayName.trim() || email.split('@')[0] || '—'}
        />
        <ReviewRow label="Slug tenant" value={tenantPreview} />
        <ReviewRow label="Ruolo" value="superuser (RBAC system)" />
        <ReviewRow
          label="Robustezza password"
          value={score >= 4 ? 'Forte' : score === 3 ? 'Buona' : 'Sufficiente'}
        />
        <ReviewRow label="Origine" value="web (loopback)" />
      </dl>
      <div className="rounded-md border border-[var(--color-warning)]/30 bg-[var(--color-warning)]/10 px-3 py-2 text-[11.5px] text-ink-muted">
        <strong className="font-semibold text-ink">Promemoria.</strong> Conserva la password in un
        gestore sicuro: il sistema non può recuperarla. Per cambiarla in seguito usa il pannello
        utente.
      </div>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────
// Atoms
// ──────────────────────────────────────────────────────────────────────────

function StepHeading({ title, body }: { title: string; body: string }) {
  return (
    <div>
      <h2 className="text-base font-semibold text-ink">{title}</h2>
      <p className="mt-1 text-[12.5px] leading-relaxed text-ink-muted">{body}</p>
    </div>
  );
}

interface FormFieldProps {
  id: string;
  label: string;
  icon: typeof Mail;
  value: string;
  onChange: (v: string) => void;
  type: string;
  autoComplete?: string;
  placeholder?: string;
  required?: boolean;
  hint?: string;
  error?: string;
  trailing?: ReactNode;
}

function FormField({
  id,
  label,
  icon: Icon,
  value,
  onChange,
  type,
  autoComplete,
  placeholder,
  required,
  hint,
  error,
  trailing,
}: FormFieldProps) {
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
        <Icon
          size={14}
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-ink-subtle"
          aria-hidden
        />
        <input
          id={id}
          type={type}
          value={value}
          onChange={(e: ChangeEvent<HTMLInputElement>) => onChange(e.target.value)}
          autoComplete={autoComplete}
          placeholder={placeholder}
          required={required}
          aria-invalid={!!error || undefined}
          aria-describedby={describedBy}
          className={cn(
            'w-full rounded-md border bg-[var(--color-canvas)] py-2 pl-9 pr-3 text-sm text-ink outline-none transition-colors focus-visible:ring-2 focus-visible:ring-[var(--color-brand-ring)] focus:border-[var(--color-brand)]',
            trailing && 'pr-10',
            error ? 'border-[var(--color-danger)]/60' : 'border-[var(--color-border)]'
          )}
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

function PasswordField({
  id,
  label,
  value,
  onChange,
  show,
  onToggleShow,
  error,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  show: boolean;
  onToggleShow: () => void;
  error?: string;
}) {
  return (
    <FormField
      id={id}
      label={label}
      icon={KeyRound}
      value={value}
      onChange={onChange}
      type={show ? 'text' : 'password'}
      autoComplete="new-password"
      required
      error={error}
      trailing={
        <button
          type="button"
          aria-label={show ? 'nascondi password' : 'mostra password'}
          onClick={onToggleShow}
          className="text-ink-subtle hover:text-ink"
        >
          {show ? <EyeOff size={14} /> : <Eye size={14} />}
        </button>
      }
    />
  );
}

function StrengthMeter({ score, label }: { score: number; label: string }) {
  const segments = 4;
  return (
    <div aria-live="polite" className="-mt-2 rounded-md bg-[var(--color-surface)] px-3 py-2">
      <div className="mb-1.5 flex items-center justify-between gap-2 text-[11px]">
        <span className="font-medium text-ink-muted">Robustezza password</span>
        <span className="text-ink-muted">{label}</span>
      </div>
      <div className="grid grid-cols-4 gap-1" aria-hidden>
        {Array.from({ length: segments }).map((_, i) => (
          <span
            key={i}
            className={cn(
              'h-1 rounded-full',
              i < score
                ? score >= 4
                  ? 'bg-[var(--color-success)]'
                  : score === 3
                    ? 'bg-[var(--color-success)]/70'
                    : score === 2
                      ? 'bg-[var(--color-warning)]'
                      : 'bg-[var(--color-danger)]'
                : 'bg-[var(--color-border)]'
            )}
          />
        ))}
      </div>
    </div>
  );
}

function ReviewRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-[var(--color-border)] bg-[var(--color-canvas)] px-3 py-2">
      <dt className="text-[10px] uppercase tracking-wider text-ink-subtle">{label}</dt>
      <dd className="mt-0.5 truncate text-sm font-medium text-ink" title={value}>
        {value}
      </dd>
    </div>
  );
}
