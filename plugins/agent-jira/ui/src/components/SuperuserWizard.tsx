/**
 * SuperuserWizard — first-boot admin creation flow for agent-jira.
 *
 * Mirrors the wikigen / dbview / docheck SuperuserWizard pattern, wired
 * to the agent-jira FastAPI bootstrap endpoints. Mounted by App.tsx
 * BEFORE LoginPage when ``GET /auth/bootstrap/status`` returns
 * ``needs_bootstrap=true`` (the POST endpoint is loopback-only).
 *
 * Steps:
 *  1. identity  — email, display name, organization (creates tenant)
 *  2. security  — password + confirm + 4-segment strength meter (≥12 chars)
 *  3. review    — explicit confirmation summary
 *
 * Reuses existing `.auth-*` and `.jw-step*` CSS so the wizard inherits
 * dark/light theme variables and animations without duplicating styles.
 */

import { useCallback, useEffect, useId, useMemo, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import {
  AlertCircle,
  ArrowLeft,
  ArrowRight,
  Building2,
  CheckCircle2,
  Eye,
  EyeOff,
  KeyRound,
  Loader2,
  Mail,
  ShieldCheck,
  Sparkles,
  User,
  type LucideIcon,
} from 'lucide-react';
import {
  bootstrapSuperuser,
  fetchBootstrapStatus,
  setStoredToken,
} from '../api/client';

const PASSWORD_MIN = 12;

type Step = 'identity' | 'security' | 'review';

interface StepMeta {
  id: Step;
  label: string;
  hint: string;
  icon: LucideIcon;
}

const STEPS: StepMeta[] = [
  { id: 'identity', label: 'Identità', hint: 'Email e organizzazione', icon: User },
  { id: 'security', label: 'Sicurezza', hint: `Password ≥${PASSWORD_MIN} char`, icon: KeyRound },
  { id: 'review', label: 'Conferma', hint: 'Crea superuser', icon: ShieldCheck },
];

interface Props {
  /** Chiamato quando il bootstrap è completato (o non necessario). */
  onComplete: () => void;
}

const SuperuserWizard = ({ onComplete }: Props) => {
  const [checking, setChecking] = useState(true);
  const [needs, setNeeds] = useState(false);
  const [step, setStep] = useState<Step>('identity');
  const [email, setEmail] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [organization, setOrganization] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const stepBodyRef = useRef<HTMLDivElement | null>(null);

  // Status probe. fail-open lets the legacy LoginPage take over on
  // transport errors (broken backend should not strand the operator).
  useEffect(() => {
    let alive = true;
    fetchBootstrapStatus()
      .then((s) => {
        if (!alive) return;
        setNeeds(s.needs_bootstrap);
        setChecking(false);
        if (!s.needs_bootstrap) onComplete();
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

  // Auto-focus the first input on step change for keyboard accessibility.
  useEffect(() => {
    if (!needs) return;
    if (!stepBodyRef.current) return;
    const first = stepBodyRef.current.querySelector<HTMLElement>(
      'input:not([type="hidden"]):not([disabled])'
    );
    const id = window.setTimeout(() => first?.focus({ preventScroll: true }), 80);
    return () => window.clearTimeout(id);
  }, [step, needs]);

  // Client-side validation echoes backend Pydantic constraints
  // (email contains @, password ≥ PASSWORD_MIN). Keeps a quick UX loop
  // without re-importing zod just for one form.
  const emailValid = email.includes('@') && /^\S+@\S+\.\S+$/.test(email.trim());
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
      const res = await bootstrapSuperuser({
        email: email.trim().toLowerCase(),
        password,
        ...(displayName.trim() ? { display_name: displayName.trim() } : {}),
        ...(organization.trim() ? { organization: organization.trim() } : {}),
      });
      // Token store match the legacy /auth/login flow consumed by
      // useAuth, so the parent re-mount lands directly in the
      // authenticated UI without forcing a manual sign-in.
      setStoredToken(res.access_token);
      onComplete();
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Errore durante il bootstrap.';
      // Normalise the FastAPI 403 loopback message for clarity.
      if (msg.toLowerCase().includes('loopback')) {
        setError(
          'Il bootstrap è consentito solo da localhost. Apri la UI da http://127.0.0.1 sulla stessa macchina dell\'engine.'
        );
      } else {
        setError(msg);
      }
    } finally {
      setBusy(false);
    }
  }, [allValid, email, password, displayName, organization, onComplete]);

  // Enter advances / submits; Cmd/Ctrl+Enter on review submits directly.
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
      <div className="auth-page">
        <div
          className="auth-card"
          style={{ alignItems: 'center', justifyContent: 'center', minHeight: 220 }}
        >
          <Loader2 className="spin" size={20} aria-label="Verifica setup iniziale" />
        </div>
      </div>
    );
  }
  if (!needs) return null;

  return (
    <div className="auth-page" role="dialog" aria-modal="true" aria-label="setup superuser iniziale">
      <div className="auth-glow auth-glow-1" />
      <div className="auth-glow auth-glow-2" />

      <div
        className="auth-card"
        style={{ maxWidth: 720, padding: 0, overflow: 'hidden' }}
      >
        <WizardHero progressPct={progressPct} />

        <Stepper step={step} />

        <div
          ref={stepBodyRef}
          style={{ padding: '24px 28px', minHeight: 260 }}
        >
          {step === 'identity' && (
            <IdentityStep
              email={email}
              setEmail={setEmail}
              displayName={displayName}
              setDisplayName={setDisplayName}
              organization={organization}
              setOrganization={setOrganization}
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
              organization={organization}
              score={passwordScore}
            />
          )}
        </div>

        {error && (
          <div style={{ padding: '0 28px 12px' }}>
            <div className="auth-error" role="alert" style={{ marginBottom: 0 }}>
              <AlertCircle size={14} />
              <span>{error}</span>
            </div>
          </div>
        )}

        <Footer
          step={step}
          busy={busy}
          canNext={step === 'identity' ? identityValid : securityValid}
          hasAll={allValid}
          onBack={goBack}
          onNext={goNext}
          onSubmit={submit}
        />
      </div>

      <p
        style={{
          marginTop: 18,
          textAlign: 'center',
          fontSize: 11,
          color: 'var(--muted)',
          opacity: 0.7,
        }}
      >
        Loopback-only · l'endpoint è disabilitato dopo la creazione del primo admin.
      </p>
    </div>
  );
};

export default SuperuserWizard;

// ──────────────────────────────────────────────────────────────────────────
// Layout pieces
// ──────────────────────────────────────────────────────────────────────────

const WizardHero = ({ progressPct }: { progressPct: number }) => (
  <div
    style={{
      padding: '24px 28px 18px',
      borderBottom: '1px solid var(--border)',
      background:
        'linear-gradient(180deg, rgba(126, 224, 255, 0.06), transparent 60%)',
    }}
  >
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        padding: '4px 10px',
        borderRadius: 999,
        border: '1px solid var(--border)',
        background: 'var(--panel)',
        fontSize: 10,
        fontWeight: 600,
        letterSpacing: '0.12em',
        textTransform: 'uppercase',
        color: 'var(--muted)',
      }}
    >
      <ShieldCheck size={11} style={{ color: 'var(--accent)' }} />
      agent-jira · setup iniziale
    </div>
    <h1
      style={{
        margin: '12px 0 6px',
        fontSize: 22,
        fontWeight: 600,
        letterSpacing: '-0.01em',
        color: 'var(--text)',
      }}
    >
      Crea il primo amministratore
    </h1>
    <p style={{ margin: 0, color: 'var(--muted)', fontSize: 13, lineHeight: 1.5 }}>
      Nessun account esiste ancora. Questa schermata è raggiungibile solo dal browser locale e
      crea l&apos;admin che gestirà ogni utente successivo.
    </p>
    <div
      style={{
        marginTop: 14,
        height: 4,
        borderRadius: 999,
        background: 'var(--panel)',
        overflow: 'hidden',
      }}
      role="progressbar"
      aria-valuenow={progressPct}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <div
        style={{
          width: `${progressPct}%`,
          height: '100%',
          background: 'var(--accent)',
          transition: 'width 240ms cubic-bezier(0.22, 1, 0.36, 1)',
        }}
      />
    </div>
  </div>
);

const Stepper = ({ step }: { step: Step }) => {
  const stepIdx = STEPS.findIndex((s) => s.id === step);
  return (
    <ol
      style={{
        display: 'flex',
        gap: 6,
        listStyle: 'none',
        padding: '14px 28px',
        margin: 0,
        borderBottom: '1px solid var(--border)',
        background: 'var(--panel)',
      }}
      aria-label="Avanzamento setup"
    >
      {STEPS.map((s, i) => {
        const passed = i < stepIdx;
        const current = i === stepIdx;
        const Icon = s.icon;
        return (
          <li
            key={s.id}
            aria-current={current ? 'step' : undefined}
            style={{
              flex: 1,
              display: 'flex',
              alignItems: 'center',
              gap: 8,
              padding: '8px 10px',
              borderRadius: 8,
              border: `1px solid ${
                current ? 'var(--accent)' : passed ? 'rgba(48, 209, 88, 0.3)' : 'var(--border)'
              }`,
              background: current
                ? 'rgba(126, 224, 255, 0.08)'
                : passed
                  ? 'rgba(48, 209, 88, 0.06)'
                  : 'transparent',
              color: current ? 'var(--text)' : 'var(--muted)',
              fontSize: 12,
              fontWeight: current ? 600 : 500,
              minWidth: 0,
            }}
          >
            <span
              style={{
                display: 'grid',
                placeItems: 'center',
                width: 22,
                height: 22,
                borderRadius: 6,
                background: current
                  ? 'var(--accent)'
                  : passed
                    ? 'rgba(48, 209, 88, 0.15)'
                    : 'var(--panel)',
                color: current ? 'var(--bg)' : passed ? '#30d158' : 'var(--muted)',
                flexShrink: 0,
              }}
            >
              {passed ? <CheckCircle2 size={13} /> : <Icon size={13} />}
            </span>
            <span style={{ display: 'flex', flexDirection: 'column', minWidth: 0 }}>
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {s.label}
              </span>
              <span style={{ fontSize: 9.5, opacity: 0.7 }}>{s.hint}</span>
            </span>
          </li>
        );
      })}
    </ol>
  );
};

const Footer = ({
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
}) => (
  <div
    style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      gap: 12,
      padding: '14px 28px',
      borderTop: '1px solid var(--border)',
      background: 'var(--panel)',
    }}
  >
    <button
      type="button"
      onClick={onBack}
      disabled={step === 'identity' || busy}
      className="auth-toggle-btn"
      aria-label="Passo precedente"
      style={{ minWidth: 100, justifyContent: 'center' }}
    >
      <ArrowLeft size={13} /> Indietro
    </button>
    {step === 'review' ? (
      <button
        type="button"
        onClick={onSubmit}
        disabled={!hasAll || busy}
        className="auth-submit"
        style={{ width: 'auto', minWidth: 200, padding: '10px 18px' }}
      >
        {busy ? (
          <>
            <Loader2 className="spin" size={14} /> Creazione…
          </>
        ) : (
          <>
            <Sparkles size={14} /> Crea superuser
          </>
        )}
      </button>
    ) : (
      <button
        type="button"
        onClick={onNext}
        disabled={!canNext || busy}
        className="auth-submit"
        style={{ width: 'auto', minWidth: 140, padding: '10px 18px' }}
      >
        Avanti <ArrowRight size={13} />
      </button>
    )}
  </div>
);

// ──────────────────────────────────────────────────────────────────────────
// Step bodies
// ──────────────────────────────────────────────────────────────────────────

const IdentityStep = ({
  email,
  setEmail,
  displayName,
  setDisplayName,
  organization,
  setOrganization,
  emailValid,
}: {
  email: string;
  setEmail: (v: string) => void;
  displayName: string;
  setDisplayName: (v: string) => void;
  organization: string;
  setOrganization: (v: string) => void;
  emailValid: boolean;
}) => {
  const emailId = useId();
  const nameId = useId();
  const orgId = useId();
  return (
    <>
      <StepHeading
        title="Identità dell'amministratore"
        body="Email e password accedono al pannello di amministrazione. L'organizzazione crea il tenant del workspace (modificabile dalle impostazioni)."
      />
      <FormField
        id={emailId}
        label="Email"
        icon={Mail}
        type="email"
        value={email}
        onChange={setEmail}
        autoComplete="username"
        placeholder="admin@example.com"
        required
        error={email.length > 0 && !emailValid ? 'Indirizzo email non valido.' : undefined}
      />
      <FormField
        id={nameId}
        label="Nome visualizzato"
        icon={User}
        type="text"
        value={displayName}
        onChange={setDisplayName}
        autoComplete="name"
        placeholder="Admin"
        hint="Opzionale — se vuoto si usa la parte locale dell'email."
      />
      <FormField
        id={orgId}
        label="Organizzazione"
        icon={Building2}
        type="text"
        value={organization}
        onChange={setOrganization}
        placeholder="Acme srl"
        hint="Opzionale — diventa il nome del tenant. Default: nome visualizzato."
      />
    </>
  );
};

const SecurityStep = ({
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
}) => {
  const pwId = useId();
  const confirmId = useId();
  const strengthLabel =
    score >= 4 ? 'Forte' : score === 3 ? 'Buona' : score === 2 ? 'Sufficiente' : 'Debole';
  return (
    <>
      <StepHeading
        title="Imposta la password"
        body={`Minimo ${PASSWORD_MIN} caratteri. Combina lettere, numeri e simboli per aumentare la robustezza. La password viene hashata con PBKDF2 e non è mai salvata in chiaro.`}
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
    </>
  );
};

const ReviewStep = ({
  email,
  displayName,
  organization,
  score,
}: {
  email: string;
  displayName: string;
  organization: string;
  score: number;
}) => {
  const strength =
    score >= 4 ? 'Forte' : score === 3 ? 'Buona' : score === 2 ? 'Sufficiente' : 'Debole';
  const tenantPreview = organization.trim() || displayName.trim() || email.split('@')[0] || 'workspace';
  return (
    <>
      <StepHeading
        title="Conferma e crea"
        body="Verifica i dati. Confermando verrai loggato automaticamente e l'endpoint di bootstrap sarà disabilitato. Gli admin successivi si gestiscono dalla pagina Utenti."
      />
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 10 }}>
        <ReviewRow label="Email" value={email.trim().toLowerCase()} />
        <ReviewRow
          label="Nome visualizzato"
          value={displayName.trim() || email.split('@')[0] || '—'}
        />
        <ReviewRow label="Organizzazione (tenant)" value={tenantPreview} />
        <ReviewRow label="Ruolo" value="admin" />
        <ReviewRow label="Robustezza password" value={strength} />
        <ReviewRow label="Origine" value="web (loopback)" />
      </div>
      <div
        style={{
          marginTop: 14,
          padding: '10px 12px',
          borderRadius: 8,
          border: '1px solid rgba(255, 159, 10, 0.3)',
          background: 'rgba(255, 159, 10, 0.08)',
          fontSize: 11.5,
          color: '#ff9f0a',
        }}
      >
        <strong>Promemoria.</strong> Conserva la password in un gestore sicuro: agent-jira non
        può recuperarla. Per cambiarla in seguito usa la pagina Profilo.
      </div>
    </>
  );
};

// ──────────────────────────────────────────────────────────────────────────
// Atoms
// ──────────────────────────────────────────────────────────────────────────

const StepHeading = ({ title, body }: { title: string; body: string }) => (
  <div style={{ marginBottom: 16 }}>
    <h2
      style={{
        margin: '0 0 4px',
        fontSize: 14,
        fontWeight: 600,
        color: 'var(--text)',
      }}
    >
      {title}
    </h2>
    <p style={{ margin: 0, fontSize: 12.5, lineHeight: 1.5, color: 'var(--muted)' }}>{body}</p>
  </div>
);

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
  trailing?: ReactNode;
}

const FormField = ({
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
}: FormFieldProps) => {
  const hintId = `${id}-hint`;
  const errorId = `${id}-error`;
  const describedBy = error ? errorId : hint ? hintId : undefined;
  return (
    <div className="auth-field">
      <label htmlFor={id} className="auth-field-label">
        <Icon size={11} /> {label}
      </label>
      <div style={{ position: 'relative' }}>
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
          className="auth-input"
          style={{
            paddingRight: trailing ? 36 : 14,
            ...(error ? { borderColor: '#ff453a' } : {}),
          }}
        />
        {trailing && (
          <div
            style={{
              position: 'absolute',
              right: 8,
              top: '50%',
              transform: 'translateY(-50%)',
            }}
          >
            {trailing}
          </div>
        )}
      </div>
      {hint && !error && (
        <span id={hintId} className="auth-field-hint">
          {hint}
        </span>
      )}
      {error && (
        <span
          id={errorId}
          role="alert"
          style={{ fontSize: 11, color: '#ff453a', marginTop: 2 }}
        >
          {error}
        </span>
      )}
    </div>
  );
};

const PasswordField = ({
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
}) => (
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
        aria-label={show ? 'Nascondi password' : 'Mostra password'}
        onClick={onToggleShow}
        style={{
          background: 'transparent',
          border: 'none',
          color: 'var(--muted)',
          cursor: 'pointer',
          padding: 4,
          display: 'inline-flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {show ? <EyeOff size={14} /> : <Eye size={14} />}
      </button>
    }
  />
);

const StrengthMeter = ({ score, label }: { score: number; label: string }) => {
  const segments = 4;
  const color =
    score >= 4
      ? '#30d158'
      : score === 3
        ? 'rgba(48, 209, 88, 0.7)'
        : score === 2
          ? '#ff9f0a'
          : '#ff453a';
  return (
    <div
      aria-live="polite"
      style={{
        marginTop: -8,
        marginBottom: 12,
        padding: '8px 12px',
        borderRadius: 8,
        background: 'var(--panel)',
        border: '1px solid var(--border)',
      }}
    >
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          fontSize: 11,
          marginBottom: 6,
          color: 'var(--muted)',
        }}
      >
        <span>Robustezza password</span>
        <span>{label}</span>
      </div>
      <div
        aria-hidden
        style={{
          display: 'grid',
          gridTemplateColumns: `repeat(${segments}, 1fr)`,
          gap: 4,
        }}
      >
        {Array.from({ length: segments }).map((_, i) => (
          <span
            key={i}
            style={{
              height: 4,
              borderRadius: 999,
              background: i < score ? color : 'var(--border)',
            }}
          />
        ))}
      </div>
    </div>
  );
};

const ReviewRow = ({ label, value }: { label: string; value: string }) => (
  <div
    style={{
      padding: '8px 12px',
      borderRadius: 8,
      border: '1px solid var(--border)',
      background: 'var(--panel)',
    }}
  >
    <div
      style={{
        fontSize: 10,
        textTransform: 'uppercase',
        letterSpacing: '0.08em',
        color: 'var(--muted)',
        marginBottom: 2,
      }}
    >
      {label}
    </div>
    <div
      title={value}
      style={{
        fontSize: 13,
        fontWeight: 500,
        color: 'var(--text)',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        whiteSpace: 'nowrap',
      }}
    >
      {value}
    </div>
  </div>
);
