/**
 * SuperuserWizard — first-boot admin creation flow (multi-step).
 *
 * Mirrors the wikigen SuperuserWizard pattern, adapted to the dbview
 * design system (semantic CSS vars, panel/btn/input utilities, lucide
 * icons, framer-motion). Shown by AuthGate when
 * `GET /api/auth/bootstrap/status` returns `needsBootstrap=true`.
 *
 * Steps:
 *  1. identity  — email, display name
 *  2. security  — password + confirm + strength meter (12 char min)
 *  3. review    — recap + explicit confirmation
 *
 * Hard rules from CLAUDE.md observed: TS strict, no `any`, Zod boundary
 * (validation echoes BootstrapRequestSchema), no `console.log`, focus
 * rings, `aria-label` on icon buttons, color used with redundant icons.
 */

import { AnimatePresence, motion } from 'framer-motion';
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Eye,
  EyeOff,
  KeyRound,
  Lock,
  Mail,
  ShieldCheck,
  Sparkles,
  User,
} from 'lucide-react';
import {
  type ChangeEvent,
  type ComponentType,
  type ReactNode,
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from 'react';
import { api } from '../lib/api.js';
import { setSession } from '../lib/auth.js';
import { cn } from '../lib/cn.js';

const PASSWORD_MIN = 12;

type Step = 'identity' | 'security' | 'review';

interface StepMeta {
  id: Step;
  label: string;
  hint: string;
  icon: ComponentType<{ className?: string; 'aria-hidden'?: boolean }>;
}

const STEPS: StepMeta[] = [
  { id: 'identity', label: 'Identity', hint: 'Email and profile', icon: User },
  { id: 'security', label: 'Security', hint: `Password (≥${PASSWORD_MIN} chars)`, icon: KeyRound },
  { id: 'review', label: 'Confirm', hint: 'Create admin', icon: ShieldCheck },
];

interface Props {
  onComplete: () => void;
}

export function SuperuserWizard({ onComplete }: Props) {
  const [checking, setChecking] = useState(true);
  const [needs, setNeeds] = useState(false);
  const [step, setStep] = useState<Step>('identity');
  const [email, setEmail] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const stepBodyRef = useRef<HTMLDivElement | null>(null);

  // Status check. fail-open on transport error so we don't trap users
  // behind a broken endpoint — falls through to LoginPage.
  useEffect(() => {
    let alive = true;
    api
      .bootstrapStatus()
      .then((s) => {
        if (!alive) return;
        setNeeds(s.needsBootstrap);
        setChecking(false);
        if (!s.needsBootstrap) onComplete();
      })
      .catch(() => {
        if (!alive) return;
        setChecking(false);
        setNeeds(false);
        onComplete();
      });
    return () => {
      alive = false;
    };
  }, [onComplete]);

  // Auto-focus first input on step change (keyboard accessibility).
  useEffect(() => {
    if (!needs) return;
    if (!stepBodyRef.current) return;
    const first = stepBodyRef.current.querySelector<HTMLElement>(
      'input:not([type="hidden"]):not([disabled])',
    );
    const id = window.setTimeout(() => first?.focus({ preventScroll: true }), 80);
    return () => window.clearTimeout(id);
  }, [step, needs]);

  // Echoes BootstrapRequestSchema. Cheap version of the regex z.email
  // uses internally — keeps the wizard usable without pulling Zod into
  // the web bundle just for one form.
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
    [password],
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
        setError('Enter a valid email address.');
        return;
      }
      setStep('security');
    } else if (step === 'security') {
      if (!securityValid) {
        setError(
          passwordLong
            ? passwordsMatch
              ? 'Password too weak. Add numbers or symbols.'
              : 'Passwords do not match.'
            : `Password must be at least ${PASSWORD_MIN} characters.`,
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
      setError('Please complete every step before confirming.');
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await api.bootstrap({
        email: email.trim().toLowerCase(),
        password,
        ...(displayName.trim() ? { displayName: displayName.trim() } : {}),
      });
      setSession(res.accessToken, res.user);
      onComplete();
    } catch (err) {
      const status = (err as { status?: number }).status;
      const code = (err as { code?: string }).code;
      const message = err instanceof Error ? err.message : null;
      if (status === 403) {
        setError(
          code === 'forbidden'
            ? message ?? 'Bootstrap not allowed from this origin. Use a localhost browser.'
            : 'Bootstrap not allowed: an admin already exists.',
        );
      } else if (status === 429) {
        setError('Too many attempts. Please wait a minute and retry.');
      } else if (status === 400) {
        setError(message ?? 'Validation failed.');
      } else {
        setError(message ?? 'Unexpected error during bootstrap.');
      }
    } finally {
      setBusy(false);
    }
  }, [allValid, email, password, displayName, onComplete]);

  useEffect(() => {
    if (!needs) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Enter') return;
      const tag = (e.target as HTMLElement | null)?.tagName;
      if (tag === 'TEXTAREA') return;
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
    return (
      <div
        className="h-screen w-screen bg-surface-0"
        aria-hidden="true"
        aria-busy="true"
      />
    );
  }
  if (!needs) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        transition={{ duration: 0.14 }}
        className="fixed inset-0 z-50 overflow-y-auto bg-surface-0 px-3 py-4 sm:px-6 sm:py-6"
        role="dialog"
        aria-modal="true"
        aria-label="Initial admin setup"
      >
        <SuperuserHero progressPct={progressPct} />

        <motion.div
          initial={{ opacity: 0, scale: 0.96, y: 6 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.96, y: 6 }}
          transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] }}
          className="panel relative z-10 mx-auto flex h-[calc(100vh-148px)] max-h-[760px] w-full max-w-6xl overflow-hidden shadow-2xl"
        >
          <SuperuserSidebar
            stepIdx={stepIdx}
            progressPct={progressPct}
            email={email}
            displayName={displayName}
          />

          <section className="flex min-w-0 flex-1 flex-col">
            <header
              className="flex items-center justify-between border-b px-4 py-3 sm:px-5"
              style={{ borderColor: 'rgb(var(--border-subtle))' }}
            >
              <div className="inline-flex min-w-0 items-center gap-2">
                <Sparkles className="h-3.5 w-3.5 shrink-0 text-accent" aria-hidden />
                <span className="truncate text-[13px] font-semibold">
                  Create the first admin
                </span>
                <span className="hidden text-[11px] text-text-dim sm:inline">
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
                  transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] }}
                  className="px-4 py-5 sm:px-7 sm:py-7"
                >
                  {step === 'identity' && (
                    <IdentityStep
                      email={email}
                      setEmail={setEmail}
                      displayName={displayName}
                      setDisplayName={setDisplayName}
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
                  className="flex items-start gap-2 rounded border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-[12px] text-rose-300"
                >
                  <Lock className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
                  <span>{error}</span>
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
          className="mx-auto mt-6 max-w-md text-center text-[11px] text-text-dim"
        >
          <details className="inline-block text-left">
            <summary className="cursor-pointer text-text-muted hover:text-text">
              Prefer the terminal?
            </summary>
            <pre className="mt-2 inline-block rounded bg-surface-2 px-2 py-1 font-mono text-[11px] text-text-muted">
              DBVIEW_ADMIN_EMAIL=... DBVIEW_ADMIN_PASSWORD=... npm run start
            </pre>
          </details>
        </motion.footer>
      </motion.div>
    </AnimatePresence>
  );
}

// ──────────────────────────────────────────────────────────────────────────
// Layout sub-components
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
        <div
          className="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-[10px] font-semibold uppercase tracking-wide text-text-muted shadow-sm"
          style={{
            borderColor: 'rgb(var(--border-subtle))',
            background: 'rgb(var(--surface-elevated) / 0.86)',
          }}
        >
          <ShieldCheck className="h-3 w-3 text-accent" aria-hidden />
          dbview · initial setup
        </div>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">
          Create the first administrator
        </h1>
        <p className="mt-1 max-w-2xl text-[13px] leading-relaxed text-text-muted">
          No accounts exist yet. This screen is reachable only from the local browser and seeds the
          admin who will manage every subsequent user.
        </p>
      </div>
      <div className="hidden shrink-0 items-center gap-2 lg:flex">
        <div
          className="rounded-lg border px-3 py-2 shadow-sm"
          style={{
            borderColor: 'rgb(var(--border-subtle))',
            background: 'rgb(var(--surface-elevated))',
          }}
        >
          <div className="text-[10px] uppercase tracking-wider text-text-dim">Progress</div>
          <div className="mt-0.5 text-sm font-semibold tabular-nums">{progressPct}%</div>
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
    <aside
      className="hidden w-72 shrink-0 flex-col border-r p-5 lg:flex"
      style={{
        borderColor: 'rgb(var(--border-subtle))',
        background: 'rgb(var(--surface-2) / 0.4)',
      }}
    >
      <div className="flex items-center gap-2">
        <div className="grid h-9 w-9 place-items-center rounded-lg bg-accent text-accent-fg shadow-sm">
          <ShieldCheck className="h-4 w-4" aria-hidden />
        </div>
        <div className="min-w-0">
          <div className="text-sm font-semibold">Initial admin</div>
          <div className="truncate text-[11px] text-text-dim">
            {displayName || email || 'Awaiting setup'}
          </div>
        </div>
      </div>

      <div className="mt-6">
        <div className="mb-2 flex items-center justify-between text-[10px] font-semibold uppercase tracking-wider text-text-dim">
          <span>Progress</span>
          <span>
            {stepIdx + 1}/{STEPS.length}
          </span>
        </div>
        <div
          className="h-1.5 overflow-hidden rounded-full"
          style={{ background: 'rgb(var(--border))' }}
        >
          <div
            className="h-full rounded-full bg-accent transition-all"
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
                  'grid h-7 w-7 shrink-0 place-items-center rounded-lg border text-[10px]',
                  current
                    ? 'border-accent bg-accent text-accent-fg'
                    : passed
                      ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300'
                      : 'border-border-subtle bg-surface-1 text-text-dim',
                )}
              >
                {passed ? (
                  <CheckCircle2 className="h-3.5 w-3.5" aria-hidden />
                ) : (
                  <Icon className="h-3.5 w-3.5" aria-hidden />
                )}
              </span>
              <div className="min-w-0">
                <div
                  className={cn(
                    'text-[12px]',
                    current ? 'font-semibold text-text' : 'font-medium text-text-muted',
                  )}
                >
                  {s.label}
                </div>
                <div className="truncate text-[10px] text-text-dim">{s.hint}</div>
              </div>
            </li>
          );
        })}
      </ol>

      <div
        className="mt-auto rounded-lg border p-3 shadow-sm"
        style={{
          borderColor: 'rgb(var(--border-subtle))',
          background: 'rgb(var(--surface-elevated))',
        }}
      >
        <div className="text-[11px] font-semibold">Loopback only</div>
        <p className="mt-1 text-[11px] leading-relaxed text-text-muted">
          This endpoint is reachable only from localhost. For remote setups bootstrap via env vars
          before the first boot.
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
      className="border-b px-4 py-3 sm:px-5"
      style={{
        borderColor: 'rgb(var(--border-subtle))',
        background: 'rgb(var(--surface-elevated))',
      }}
      aria-label="Setup progress"
    >
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="text-[10px] font-semibold uppercase tracking-wider text-text-dim">
          Guided setup
        </div>
        <div className="text-[10px] tabular-nums text-text-dim">
          Step {stepIdx + 1} of {STEPS.length}
        </div>
      </div>
      <div
        className="mb-3 h-1 overflow-hidden rounded-full"
        style={{ background: 'rgb(var(--surface-2))' }}
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className="h-full rounded-full bg-accent transition-[width] duration-300 ease-out"
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
                  ? 'border-accent bg-accent/15 text-text shadow-sm'
                  : passed
                    ? 'border-emerald-500/25 bg-emerald-500/10 text-text-muted'
                    : 'border-border-subtle bg-surface-1 text-text-dim',
              )}
            >
              <span
                className={cn(
                  'grid h-6 w-6 shrink-0 place-items-center rounded-md border text-[10px] font-semibold',
                  current
                    ? 'border-accent bg-accent text-accent-fg'
                    : passed
                      ? 'border-emerald-500/30 bg-emerald-500/15 text-emerald-300'
                      : 'border-border-subtle bg-surface-2 text-text-dim',
                )}
              >
                {passed ? (
                  <CheckCircle2 className="h-3 w-3" aria-hidden />
                ) : (
                  <Icon className="h-3 w-3" aria-hidden />
                )}
              </span>
              <span className="min-w-0">
                <span
                  className={cn(
                    'block truncate text-[11.5px]',
                    current ? 'font-semibold' : 'font-medium',
                  )}
                >
                  {s.label}
                </span>
                <span className="block truncate text-[9.5px] text-text-dim">{s.hint}</span>
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
    <footer
      className="border-t px-4 py-3 sm:px-5"
      style={{
        borderColor: 'rgb(var(--border-subtle))',
        background: 'rgb(var(--surface-elevated))',
      }}
    >
      <div className="flex items-center justify-between gap-3">
        <button
          type="button"
          className="btn-ghost"
          disabled={step === 'identity' || busy}
          onClick={onBack}
          aria-label="Previous step"
        >
          <ArrowLeft className="h-3.5 w-3.5" aria-hidden /> Back
        </button>
        <div className="hidden min-w-0 flex-1 text-center sm:block">
          <div className="text-[11px] font-medium text-text-muted">{footerTitle(step)}</div>
          <div className="text-[10px] text-text-dim">
            {stepIdx + 1}/{STEPS.length} · {footerHint(step)}
          </div>
        </div>
        {step === 'review' ? (
          <button
            type="button"
            className="btn-primary"
            disabled={!hasAll || busy}
            onClick={onSubmit}
          >
            <Sparkles className="h-3.5 w-3.5" aria-hidden />
            {busy ? 'Creating…' : 'Create admin'}
          </button>
        ) : (
          <button
            type="button"
            className="btn-primary"
            disabled={!canNext || busy}
            onClick={onNext}
          >
            Next <ArrowRight className="h-3.5 w-3.5" aria-hidden />
          </button>
        )}
      </div>
    </footer>
  );
}

function footerTitle(step: Step): string {
  switch (step) {
    case 'identity':
      return 'Define the administrator identity';
    case 'security':
      return 'Set a strong password';
    default:
      return 'Confirm and create the admin';
  }
}

function footerHint(step: Step): string {
  switch (step) {
    case 'identity':
      return 'email, display name';
    case 'security':
      return `min ${PASSWORD_MIN} chars, never logged`;
    default:
      return 'irreversible once an admin exists';
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
  emailValid,
}: {
  email: string;
  setEmail: (v: string) => void;
  displayName: string;
  setDisplayName: (v: string) => void;
  emailValid: boolean;
}) {
  const emailId = useId();
  const nameId = useId();
  return (
    <div className="mx-auto flex max-w-xl flex-col gap-4">
      <StepHeading
        title="Administrator identity"
        body="These credentials will be used to access the admin console. Email and password remain editable after first sign-in."
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
        error={email.length > 0 && !emailValid ? 'Invalid email address.' : undefined}
      />
      <FormField
        id={nameId}
        label="Display name"
        icon={User}
        value={displayName}
        onChange={setDisplayName}
        type="text"
        autoComplete="name"
        placeholder="Admin"
        hint="Optional — defaults to “Admin” if blank."
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
    score >= 4 ? 'Strong' : score === 3 ? 'Good' : score === 2 ? 'Fair' : 'Weak';
  return (
    <div className="mx-auto flex max-w-xl flex-col gap-4">
      <StepHeading
        title="Set the password"
        body={`Minimum ${PASSWORD_MIN} characters. Mix letters, digits and symbols to maximise robustness. The password is hashed with argon2id and never stored in plaintext.`}
      />
      <PasswordField
        id={pwId}
        label={`Password (min ${PASSWORD_MIN} chars)`}
        value={password}
        onChange={setPassword}
        show={showPw}
        onToggleShow={onToggleShow}
        error={tooShort ? `Need at least ${PASSWORD_MIN} characters.` : undefined}
      />
      <StrengthMeter score={score} label={strengthLabel} />
      <PasswordField
        id={confirmId}
        label="Confirm password"
        value={confirm}
        onChange={setConfirm}
        show={showPw}
        onToggleShow={onToggleShow}
        error={mismatch ? 'Passwords do not match.' : undefined}
      />
    </div>
  );
}

function ReviewStep({
  email,
  displayName,
  score,
}: {
  email: string;
  displayName: string;
  score: number;
}) {
  const strength = score >= 4 ? 'Strong' : score === 3 ? 'Good' : 'Fair';
  return (
    <div className="mx-auto flex max-w-xl flex-col gap-4">
      <StepHeading
        title="Confirm and create"
        body="Review the data below. Confirming will log you in immediately and disable the bootstrap endpoint. Further admins are then managed from the users dialog."
      />
      <dl className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <ReviewRow label="Email" value={email.trim().toLowerCase()} />
        <ReviewRow
          label="Display name"
          value={displayName.trim() || 'Admin'}
        />
        <ReviewRow label="Role" value="admin (RBAC)" />
        <ReviewRow label="Password strength" value={strength} />
        <ReviewRow label="Source" value="web (loopback)" />
        <ReviewRow label="Force password change" value="No" />
      </dl>
      <div
        className="rounded-md border px-3 py-2 text-[11.5px] text-text-muted"
        style={{
          borderColor: 'rgb(var(--border-subtle))',
          background: 'rgb(var(--surface-2) / 0.6)',
        }}
      >
        <strong className="font-semibold text-text">Reminder.</strong> Save the password in a
        password manager: dbview cannot recover it. Use the user menu to change it later.
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
      <h2 className="text-[15px] font-semibold tracking-tight">{title}</h2>
      <p className="mt-1 text-[12.5px] leading-relaxed text-text-muted">{body}</p>
    </div>
  );
}

interface FormFieldProps {
  id: string;
  label: string;
  icon: ComponentType<{ className?: string; 'aria-hidden'?: boolean }>;
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
        className="mb-1 block text-[11px] font-medium uppercase tracking-wider text-text-muted"
      >
        {label}
      </label>
      <div className="relative">
        <Icon className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-text-dim" aria-hidden />
        <input
          id={id}
          type={type}
          value={value}
          onChange={(e: ChangeEvent<HTMLInputElement>) => onChange(e.target.value)}
          autoComplete={autoComplete}
          placeholder={placeholder}
          required={required}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          className={cn(
            'input pl-9 pr-3',
            trailing && 'pr-10',
            error && '!border-rose-500/60 focus:!border-rose-500/60',
          )}
        />
        {trailing && (
          <div className="absolute right-2 top-1/2 -translate-y-1/2">{trailing}</div>
        )}
      </div>
      {hint && !error && (
        <span id={hintId} className="mt-1 block text-[11px] text-text-muted">
          {hint}
        </span>
      )}
      {error && (
        <span id={errorId} role="alert" className="mt-1 block text-[11px] text-rose-300">
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
          aria-label={show ? 'Hide password' : 'Show password'}
          onClick={onToggleShow}
          className="focus:outline-none focus:ring-2 focus:ring-accent text-text-dim hover:text-text"
        >
          {show ? (
            <EyeOff className="h-3.5 w-3.5" aria-hidden />
          ) : (
            <Eye className="h-3.5 w-3.5" aria-hidden />
          )}
        </button>
      }
    />
  );
}

function StrengthMeter({ score, label }: { score: number; label: string }) {
  const segments = 4;
  return (
    <div
      aria-live="polite"
      className="-mt-2 rounded-md px-3 py-2"
      style={{ background: 'rgb(var(--surface-2) / 0.6)' }}
    >
      <div className="mb-1.5 flex items-center justify-between gap-2 text-[11px]">
        <span className="font-medium text-text-muted">Password robustness</span>
        <span className="text-text-muted">{label}</span>
      </div>
      <div className="grid grid-cols-4 gap-1" aria-hidden>
        {Array.from({ length: segments }).map((_, i) => (
          <span
            key={i}
            className={cn(
              'h-1 rounded-full',
              i < score
                ? score >= 4
                  ? 'bg-emerald-400'
                  : score === 3
                    ? 'bg-emerald-400/70'
                    : score === 2
                      ? 'bg-amber-400'
                      : 'bg-rose-400'
                : 'bg-border',
            )}
          />
        ))}
      </div>
    </div>
  );
}

function ReviewRow({ label, value }: { label: string; value: string }) {
  return (
    <div
      className="rounded-md border px-3 py-2"
      style={{
        borderColor: 'rgb(var(--border-subtle))',
        background: 'rgb(var(--surface-0) / 0.55)',
      }}
    >
      <dt className="text-[10px] uppercase tracking-wider text-text-dim">{label}</dt>
      <dd className="mt-0.5 truncate text-[13px] font-medium" title={value}>
        {value}
      </dd>
    </div>
  );
}
