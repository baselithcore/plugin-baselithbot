'use client';

/**
 * SuperuserWizard — first-boot admin creation flow for docheck.
 *
 * Mirrors the wikigen / dbview SuperuserWizard pattern, adapted to the
 * docheck Next.js + next-intl + Tailwind design system. Self-checks
 * `GET /auth/bootstrap/status` and posts `POST /auth/bootstrap` (the
 * endpoint is loopback-only when no user exists). On success the session
 * token is stored and the user is redirected to the protected shell.
 *
 * Steps:
 *  1. identity  — email, display name
 *  2. security  — password + confirm + strength meter (12 char min)
 *  3. review    — recap + explicit confirmation
 */

import { useCallback, useEffect, useId, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  Eye,
  EyeOff,
  KeyRound,
  Mail,
  ShieldCheck,
  Sparkles,
  User,
  type LucideIcon,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/cn';

const PASSWORD_MIN = 12;
const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://127.0.0.1:8765/api/v1';
const TOKEN_KEY = 'docheck.token';

type Step = 'identity' | 'security' | 'review';

interface StepMeta {
  id: Step;
  icon: LucideIcon;
}

const STEPS: StepMeta[] = [
  { id: 'identity', icon: User },
  { id: 'security', icon: KeyRound },
  { id: 'review', icon: ShieldCheck },
];

interface BootstrapStatus {
  needs_bootstrap: boolean;
  users_count: number;
}

interface BootstrapResponse {
  user_id: string;
  email: string;
  roles: string[];
  token: string;
}

export default function SuperuserSetupPage() {
  const t = useTranslations('superuserSetup');
  const router = useRouter();

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

  // Status check. Redirect to /login when bootstrap already done — keeps
  // a stale browser tab pointing at /superuser-setup from blocking the
  // legitimate sign-in path after an admin has been provisioned.
  useEffect(() => {
    let alive = true;
    fetch(`${API_BASE}/auth/bootstrap/status`)
      .then((r) => (r.ok ? (r.json() as Promise<BootstrapStatus>) : null))
      .then((s) => {
        if (!alive) return;
        const ok = s ? s.needs_bootstrap : false;
        setNeeds(ok);
        setChecking(false);
        if (!ok) router.replace('/login');
      })
      .catch(() => {
        if (!alive) return;
        setChecking(false);
        setNeeds(false);
        router.replace('/login');
      });
    return () => {
      alive = false;
    };
  }, [router]);

  // Auto-focus first input on step change.
  useEffect(() => {
    if (!needs) return;
    if (!stepBodyRef.current) return;
    const first = stepBodyRef.current.querySelector<HTMLElement>(
      'input:not([type="hidden"]):not([disabled])'
    );
    const id = window.setTimeout(() => first?.focus({ preventScroll: true }), 80);
    return () => window.clearTimeout(id);
  }, [step, needs]);

  // Validation — mirrors backend Pydantic rules (email regex + min 12).
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
        setError(t('errors.invalidEmail'));
        return;
      }
      setStep('security');
    } else if (step === 'security') {
      if (!securityValid) {
        setError(
          passwordLong
            ? passwordsMatch
              ? t('errors.weakPassword')
              : t('errors.passwordMismatch')
            : t('errors.passwordShort', { min: PASSWORD_MIN })
        );
        return;
      }
      setStep('review');
    }
  }, [step, identityValid, securityValid, passwordLong, passwordsMatch, t]);

  const goBack = useCallback(() => {
    setError(null);
    if (step === 'security') setStep('identity');
    else if (step === 'review') setStep('security');
  }, [step]);

  const submit = useCallback(async () => {
    if (!allValid) {
      setError(t('errors.incomplete'));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/auth/bootstrap`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: email.trim().toLowerCase(),
          password,
          ...(displayName.trim() ? { display_name: displayName.trim() } : {}),
        }),
      });
      if (!res.ok) {
        if (res.status === 403) throw new Error(t('errors.forbidden'));
        if (res.status === 422 || res.status === 400) throw new Error(t('errors.validation'));
        throw new Error(t('errors.generic', { status: res.status }));
      }
      const session = (await res.json()) as BootstrapResponse;
      localStorage.setItem(TOKEN_KEY, session.token);
      localStorage.setItem(`${TOKEN_KEY}.session`, JSON.stringify(session));
      router.replace('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : t('errors.generic', { status: '?' }));
    } finally {
      setBusy(false);
    }
  }, [allValid, email, password, displayName, router, t]);

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
    return <div className="min-h-screen bg-bg-canvas" aria-busy="true" />;
  }
  if (!needs) return null;

  return (
    <div className="min-h-screen relative overflow-hidden bg-bg-canvas px-4 py-6 sm:px-6 sm:py-8">
      <WizardHero progressPct={progressPct} t={t} />

      <div className="mx-auto mt-4 flex h-[calc(100vh-180px)] max-h-[760px] w-full max-w-6xl overflow-hidden rounded-lg border border-border surface-elev shadow-panel animate-fade-in">
        <WizardSidebar
          stepIdx={stepIdx}
          progressPct={progressPct}
          email={email}
          displayName={displayName}
          t={t}
        />

        <section className="flex min-w-0 flex-1 flex-col">
          <header className="flex items-center justify-between border-b border-border px-4 py-3 sm:px-5">
            <div className="inline-flex min-w-0 items-center gap-2">
              <Sparkles className="h-3.5 w-3.5 shrink-0 text-status-info" aria-hidden />
              <span className="truncate text-[13px] font-semibold text-text-primary">
                {t('header.title')}
              </span>
              <span className="hidden text-[11px] text-text-muted sm:inline">
                {t('header.subtitle')}
              </span>
            </div>
          </header>

          <div className="lg:hidden">
            <WizardStepper step={step} t={t} />
          </div>

          <div ref={stepBodyRef} className="flex-1 overflow-y-auto">
            <div key={step} className="animate-fade-in px-4 py-5 sm:px-7 sm:py-7">
              {step === 'identity' && (
                <IdentityStep
                  email={email}
                  setEmail={setEmail}
                  displayName={displayName}
                  setDisplayName={setDisplayName}
                  emailValid={emailValid}
                  t={t}
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
                  t={t}
                />
              )}
              {step === 'review' && (
                <ReviewStep email={email} displayName={displayName} score={passwordScore} t={t} />
              )}
            </div>
          </div>

          {error && (
            <div className="px-4 pb-2 sm:px-7">
              <p
                role="alert"
                className="rounded-md border border-status-danger/30 bg-status-danger/10 px-3 py-2 text-xs text-status-danger"
              >
                {error}
              </p>
            </div>
          )}

          <WizardFooter
            step={step}
            busy={busy}
            canNext={step === 'identity' ? identityValid : securityValid}
            hasAll={allValid}
            onBack={goBack}
            onNext={goNext}
            onSubmit={submit}
            t={t}
          />
        </section>
      </div>

      <footer className="mx-auto mt-6 max-w-md text-center text-[11px] text-text-muted">
        <details className="inline-block text-left">
          <summary className="cursor-pointer hover:text-text-primary">{t('cliHint.label')}</summary>
          <pre className="mt-2 inline-block rounded-md border border-border bg-bg-canvas px-2 py-1 font-mono text-[11px] text-text-secondary">
            uv run python scripts/seed_admin.py
          </pre>
        </details>
      </footer>
    </div>
  );
}

// ──────────────────────────────────────────────────────────────────────────
// Layout sub-components
// ──────────────────────────────────────────────────────────────────────────

type T = ReturnType<typeof useTranslations<'superuserSetup'>>;

function WizardHero({ progressPct, t }: { progressPct: number; t: T }) {
  return (
    <header className="mx-auto flex w-full max-w-6xl items-center justify-between gap-4 animate-fade-in">
      <div className="min-w-0">
        <div className="inline-flex items-center gap-2 rounded-full border border-border bg-bg-panel-elev px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.18em] text-text-muted shadow-sm">
          <ShieldCheck className="h-3 w-3 text-status-info" aria-hidden />
          {t('hero.badge')}
        </div>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight text-text-primary sm:text-3xl">
          {t('hero.title')}
        </h1>
        <p className="mt-1 max-w-2xl text-[13px] leading-relaxed text-text-secondary">
          {t('hero.body')}
        </p>
      </div>
      <div className="hidden shrink-0 items-center gap-2 lg:flex">
        <div className="rounded-lg border border-border bg-bg-panel-elev px-3 py-2 shadow-sm">
          <div className="text-[10px] uppercase tracking-wider text-text-muted">
            {t('hero.progressLabel')}
          </div>
          <div className="mt-0.5 text-sm font-semibold tabular-nums text-text-primary">
            {progressPct}%
          </div>
        </div>
      </div>
    </header>
  );
}

function WizardSidebar({
  stepIdx,
  progressPct,
  email,
  displayName,
  t,
}: {
  stepIdx: number;
  progressPct: number;
  email: string;
  displayName: string;
  t: T;
}) {
  return (
    <aside className="hidden w-72 shrink-0 flex-col border-r border-border bg-bg-panel/40 p-5 lg:flex">
      <div className="flex items-center gap-2">
        <div className="grid h-9 w-9 place-items-center rounded-md border border-status-info/40 bg-status-info/10 text-status-info">
          <ShieldCheck className="h-4 w-4" aria-hidden />
        </div>
        <div className="min-w-0">
          <div className="text-sm font-semibold text-text-primary">{t('sidebar.title')}</div>
          <div className="truncate text-[11px] text-text-muted">
            {displayName || email || t('sidebar.placeholder')}
          </div>
        </div>
      </div>

      <div className="mt-6">
        <div className="mb-2 flex items-center justify-between text-[10px] font-semibold uppercase tracking-wider text-text-muted">
          <span>{t('sidebar.progress')}</span>
          <span>
            {stepIdx + 1}/{STEPS.length}
          </span>
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-border">
          <div
            className="h-full rounded-full bg-status-info transition-all"
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
                  'grid h-7 w-7 shrink-0 place-items-center rounded-md border text-[10px]',
                  current
                    ? 'border-status-info bg-status-info text-white'
                    : passed
                      ? 'border-status-success/30 bg-status-success/10 text-status-success'
                      : 'border-border bg-bg-panel-elev text-text-muted'
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
                    current
                      ? 'font-semibold text-text-primary'
                      : 'font-medium text-text-secondary'
                  )}
                >
                  {t(`steps.${s.id}.label`)}
                </div>
                <div className="truncate text-[10px] text-text-muted">
                  {t(`steps.${s.id}.hint`)}
                </div>
              </div>
            </li>
          );
        })}
      </ol>

      <div className="mt-auto rounded-md border border-status-warning/30 bg-status-warning/10 p-3 text-[11px] text-status-warning">
        <div className="font-semibold">{t('sidebar.loopback.title')}</div>
        <p className="mt-1 leading-relaxed">{t('sidebar.loopback.body')}</p>
      </div>
    </aside>
  );
}

function WizardStepper({ step, t }: { step: Step; t: T }) {
  const stepIdx = STEPS.findIndex((s) => s.id === step);
  const pct = Math.round(((stepIdx + 1) / STEPS.length) * 100);
  return (
    <nav
      className="border-b border-border bg-bg-panel-elev px-4 py-3 sm:px-5"
      aria-label={t('stepper.aria')}
    >
      <div className="mb-3 flex items-center justify-between gap-3">
        <div className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">
          {t('stepper.title')}
        </div>
        <div className="text-[10px] tabular-nums text-text-muted">
          {t('stepper.step', { current: stepIdx + 1, total: STEPS.length })}
        </div>
      </div>
      <div
        className="mb-3 h-1 overflow-hidden rounded-full bg-border"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div className="h-full rounded-full bg-status-info transition-all" style={{ width: `${pct}%` }} />
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
                'inline-flex min-w-[8.25rem] items-center gap-2 rounded-md border px-2.5 py-2 text-left',
                current
                  ? 'border-status-info bg-status-info/15 text-text-primary shadow-sm'
                  : passed
                    ? 'border-status-success/25 bg-status-success/10 text-text-secondary'
                    : 'border-border bg-bg-panel text-text-muted'
              )}
            >
              <span
                className={cn(
                  'grid h-6 w-6 shrink-0 place-items-center rounded-md border text-[10px] font-semibold',
                  current
                    ? 'border-status-info bg-status-info text-white'
                    : passed
                      ? 'border-status-success/30 bg-status-success/15 text-status-success'
                      : 'border-border bg-bg-panel-elev text-text-muted'
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
                    current ? 'font-semibold' : 'font-medium'
                  )}
                >
                  {t(`steps.${s.id}.label`)}
                </span>
                <span className="block truncate text-[9.5px] text-text-muted">
                  {t(`steps.${s.id}.hint`)}
                </span>
              </span>
            </div>
          );
        })}
      </div>
    </nav>
  );
}

function WizardFooter({
  step,
  busy,
  canNext,
  hasAll,
  onBack,
  onNext,
  onSubmit,
  t,
}: {
  step: Step;
  busy: boolean;
  canNext: boolean;
  hasAll: boolean;
  onBack: () => void;
  onNext: () => void;
  onSubmit: () => void;
  t: T;
}) {
  const stepIdx = STEPS.findIndex((s) => s.id === step);
  return (
    <footer className="border-t border-border bg-bg-panel/50 px-4 py-3 sm:px-5">
      <div className="flex items-center justify-between gap-3">
        <Button
          variant="ghost"
          size="sm"
          disabled={step === 'identity' || busy}
          onClick={onBack}
        >
          <ArrowLeft size={13} /> {t('footer.back')}
        </Button>
        <div className="hidden min-w-0 flex-1 text-center sm:block">
          <div className="text-[11px] font-medium text-text-secondary">
            {t(`footer.title.${step}`)}
          </div>
          <div className="text-[10px] text-text-muted">
            {stepIdx + 1}/{STEPS.length} · {t(`footer.hint.${step}`)}
          </div>
        </div>
        {step === 'review' ? (
          <Button variant="primary" size="sm" disabled={!hasAll || busy} onClick={onSubmit}>
            <Sparkles size={13} />
            {busy ? t('footer.creating') : t('footer.create')}
          </Button>
        ) : (
          <Button variant="primary" size="sm" disabled={!canNext || busy} onClick={onNext}>
            {t('footer.next')} <ArrowRight size={13} />
          </Button>
        )}
      </div>
    </footer>
  );
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
  t,
}: {
  email: string;
  setEmail: (v: string) => void;
  displayName: string;
  setDisplayName: (v: string) => void;
  emailValid: boolean;
  t: T;
}) {
  const emailId = useId();
  const nameId = useId();
  return (
    <div className="mx-auto flex max-w-xl flex-col gap-4">
      <StepHeading title={t('identity.title')} body={t('identity.body')} />
      <FormField
        id={emailId}
        label={t('identity.email')}
        icon={Mail}
        value={email}
        onChange={setEmail}
        type="email"
        autoComplete="username"
        placeholder="admin@example.com"
        required
        error={email.length > 0 && !emailValid ? t('errors.invalidEmail') : undefined}
      />
      <FormField
        id={nameId}
        label={t('identity.displayName')}
        icon={User}
        value={displayName}
        onChange={setDisplayName}
        type="text"
        autoComplete="name"
        placeholder="Admin"
        hint={t('identity.displayNameHint')}
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
  t,
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
  t: T;
}) {
  const pwId = useId();
  const confirmId = useId();
  const strengthLabel =
    score >= 4
      ? t('security.strength.strong')
      : score === 3
        ? t('security.strength.good')
        : score === 2
          ? t('security.strength.fair')
          : t('security.strength.weak');
  return (
    <div className="mx-auto flex max-w-xl flex-col gap-4">
      <StepHeading
        title={t('security.title')}
        body={t('security.body', { min: PASSWORD_MIN })}
      />
      <PasswordField
        id={pwId}
        label={t('security.password', { min: PASSWORD_MIN })}
        value={password}
        onChange={setPassword}
        show={showPw}
        onToggleShow={onToggleShow}
        error={tooShort ? t('errors.passwordShort', { min: PASSWORD_MIN }) : undefined}
      />
      <StrengthMeter score={score} label={strengthLabel} t={t} />
      <PasswordField
        id={confirmId}
        label={t('security.confirm')}
        value={confirm}
        onChange={setConfirm}
        show={showPw}
        onToggleShow={onToggleShow}
        error={mismatch ? t('errors.passwordMismatch') : undefined}
      />
    </div>
  );
}

function ReviewStep({
  email,
  displayName,
  score,
  t,
}: {
  email: string;
  displayName: string;
  score: number;
  t: T;
}) {
  const strength =
    score >= 4 ? t('security.strength.strong') : score === 3 ? t('security.strength.good') : t('security.strength.fair');
  return (
    <div className="mx-auto flex max-w-xl flex-col gap-4">
      <StepHeading title={t('review.title')} body={t('review.body')} />
      <dl className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <ReviewRow label={t('review.rows.email')} value={email.trim().toLowerCase()} />
        <ReviewRow
          label={t('review.rows.displayName')}
          value={displayName.trim() || email.split('@')[0] || '—'}
        />
        <ReviewRow label={t('review.rows.role')} value={t('review.rows.roleValue')} />
        <ReviewRow label={t('review.rows.passwordStrength')} value={strength} />
        <ReviewRow label={t('review.rows.source')} value={t('review.rows.sourceValue')} />
        <ReviewRow label={t('review.rows.forcedChange')} value={t('review.rows.forcedChangeValue')} />
      </dl>
      <div className="rounded-md border border-status-warning/30 bg-status-warning/10 px-3 py-2 text-[11.5px] text-status-warning">
        <strong className="font-semibold">{t('review.reminder.title')}</strong>{' '}
        {t('review.reminder.body')}
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
      <h2 className="text-[15px] font-semibold tracking-tight text-text-primary">{title}</h2>
      <p className="mt-1 text-[12.5px] leading-relaxed text-text-secondary">{body}</p>
    </div>
  );
}

interface FormFieldProps {
  id: string;
  label: string;
  icon: LucideIcon;
  value: string;
  onChange: (v: string) => void;
  type: string;
  autoComplete?: string;
  placeholder?: string;
  required?: boolean;
  hint?: string;
  error?: string;
  trailing?: React.ReactNode;
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
        <Icon
          className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-text-muted"
          aria-hidden
        />
        <input
          id={id}
          type={type}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          autoComplete={autoComplete}
          placeholder={placeholder}
          required={required}
          aria-invalid={error ? true : undefined}
          aria-describedby={describedBy}
          className={cn(
            'h-10 w-full rounded-md border bg-bg-canvas pl-9 pr-3 text-sm text-text-primary outline-none transition-colors focus:border-status-info/60 focus:ring-2 focus:ring-status-info/20',
            trailing && 'pr-10',
            error ? 'border-status-danger/60' : 'border-border'
          )}
        />
        {trailing && <div className="absolute right-2 top-1/2 -translate-y-1/2">{trailing}</div>}
      </div>
      {hint && !error && (
        <span id={hintId} className="mt-1 block text-[11px] text-text-muted">
          {hint}
        </span>
      )}
      {error && (
        <span
          id={errorId}
          role="alert"
          className="mt-1 block text-[11px] text-status-danger"
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
          aria-label={show ? 'Hide password' : 'Show password'}
          onClick={onToggleShow}
          className="text-text-muted hover:text-text-primary focus:outline-none focus:ring-2 focus:ring-status-info/40"
        >
          {show ? <EyeOff className="h-3.5 w-3.5" aria-hidden /> : <Eye className="h-3.5 w-3.5" aria-hidden />}
        </button>
      }
    />
  );
}

function StrengthMeter({ score, label, t }: { score: number; label: string; t: T }) {
  const segments = 4;
  return (
    <div aria-live="polite" className="-mt-2 rounded-md bg-bg-panel/60 px-3 py-2">
      <div className="mb-1.5 flex items-center justify-between gap-2 text-[11px]">
        <span className="font-medium text-text-secondary">{t('security.strength.label')}</span>
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
                  ? 'bg-status-success'
                  : score === 3
                    ? 'bg-status-success/70'
                    : score === 2
                      ? 'bg-status-warning'
                      : 'bg-status-danger'
                : 'bg-border'
            )}
          />
        ))}
      </div>
    </div>
  );
}

function ReviewRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-md border border-border bg-bg-canvas px-3 py-2">
      <dt className="text-[10px] uppercase tracking-wider text-text-muted">{label}</dt>
      <dd className="mt-0.5 truncate text-[13px] font-medium text-text-primary" title={value}>
        {value}
      </dd>
    </div>
  );
}
