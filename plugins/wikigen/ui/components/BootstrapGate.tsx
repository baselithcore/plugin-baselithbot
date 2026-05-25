/**
 * BootstrapGate — first-boot superuser creation flow.
 *
 * Mostrato da App.tsx PRIMA di auth/setup quando
 * ``GET /auth/bootstrap/status`` ritorna ``needs_bootstrap=true``.
 * L'endpoint backend è loopback-only durante questo stato — il form
 * gira sotto localhost durante il primo deploy.
 *
 * Flow:
 *   1. fetch status. Se needs_bootstrap=false → onComplete() immediato.
 *   2. mostra form (email + password + confirm + display name).
 *   3. POST /auth/bootstrap → access token + refresh cookie. AuthContext
 *      raccoglie via /auth/me al refresh successivo.
 *   4. onComplete() → App rimonta, salta a SetupWizard.
 *
 * Best practice 2026:
 * - Password mai pre-compilata o suggerita.
 * - Validazione client (≥12 char) speculare al backend Pydantic.
 * - Toggle show/hide password (ARIA-labeled).
 * - No autocomplete suggestions sul campo password (`new-password`).
 */

import { useEffect, useId, useState, type FormEvent } from 'react';
import { Eye, EyeOff, KeyRound, Mail, ShieldCheck, User } from 'lucide-react';

import * as authApi from '../lib/api/auth';
import { useAuth } from '../contexts/AuthContext';
import { Button } from './ui/Button';

const PASSWORD_MIN = 12;

interface Props {
  /** Chiamato quando il bootstrap è completato (o non necessario). */
  onComplete: () => void;
}

export function BootstrapGate({ onComplete }: Props) {
  const [checking, setChecking] = useState(true);
  const [needsBootstrap, setNeedsBootstrap] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { refreshUser } = useAuth();

  const emailId = useId();
  const pwId = useId();
  const confirmId = useId();
  const nameId = useId();

  useEffect(() => {
    const ac = new AbortController();
    authApi
      .bootstrapStatus(ac.signal)
      .then((s) => {
        setNeedsBootstrap(s.needs_bootstrap);
        setChecking(false);
        if (!s.needs_bootstrap) {
          onComplete();
        }
      })
      .catch(() => {
        // DB irraggiungibile / auth disabilitato → lascia App al gate auth normale.
        setChecking(false);
        setNeedsBootstrap(false);
        onComplete();
      });
    return () => ac.abort();
  }, [onComplete]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!email.trim() || !password) {
      setError('Email e password obbligatorie.');
      return;
    }
    if (password.length < PASSWORD_MIN) {
      setError(`Password deve essere di almeno ${PASSWORD_MIN} caratteri.`);
      return;
    }
    if (password !== confirm) {
      setError('Le password non coincidono.');
      return;
    }

    setBusy(true);
    try {
      await authApi.bootstrap({
        email: email.trim().toLowerCase(),
        password,
        display_name: displayName.trim(),
      });
      // Login implicito già avvenuto: AuthContext non l'ha visto perché
      // siamo fuori dal flow di login. Forziamo refresh user.
      await refreshUser();
      onComplete();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Errore durante il bootstrap.'
      );
    } finally {
      setBusy(false);
    }
  };

  if (checking) {
    return <div className="h-screen w-screen bg-canvas" aria-hidden="true" />;
  }
  if (!needsBootstrap) {
    return null;
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas px-4 py-10">
      <div className="w-full max-w-md rounded-2xl border border-[var(--color-border)] bg-[var(--color-canvas-raised)] p-8 shadow-xl">
        <header className="mb-6 flex flex-col items-center gap-2 text-center">
          <ShieldCheck size={32} className="text-[var(--color-brand)]" />
          <h1 className="text-lg font-semibold text-ink">Configurazione iniziale</h1>
          <p className="max-w-sm text-xs text-ink-subtle">
            Nessun amministratore configurato. Crea il primo{' '}
            <strong>superuser</strong> per iniziare. Questo passaggio è
            disponibile solo dal browser locale (loopback).
          </p>
        </header>

        <form onSubmit={submit} className="flex flex-col gap-3">
          <Field
            id={emailId}
            label="Email"
            icon={Mail}
            type="email"
            autoComplete="username"
            value={email}
            onChange={setEmail}
            placeholder="admin@example.com"
            required
            disabled={busy}
          />
          <Field
            id={nameId}
            label="Nome visualizzato (opzionale)"
            icon={User}
            type="text"
            autoComplete="name"
            value={displayName}
            onChange={setDisplayName}
            placeholder="Admin"
            disabled={busy}
          />
          <PasswordField
            id={pwId}
            label={`Password (min ${PASSWORD_MIN} caratteri)`}
            value={password}
            onChange={setPassword}
            show={showPw}
            onToggleShow={() => setShowPw((v) => !v)}
            disabled={busy}
          />
          <PasswordField
            id={confirmId}
            label="Conferma password"
            value={confirm}
            onChange={setConfirm}
            show={showPw}
            onToggleShow={() => setShowPw((v) => !v)}
            disabled={busy}
          />

          {error && (
            <p
              role="alert"
              className="rounded border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400"
            >
              {error}
            </p>
          )}

          <Button
            type="submit"
            variant="primary"
            disabled={busy}
            className="mt-2"
          >
            {busy ? 'Creazione…' : 'Crea superuser e continua'}
          </Button>
        </form>

        <p className="mt-5 text-[10px] text-ink-subtle">
          Alternativa CLI: <code>wiki-wl create-superuser</code> dal terminale.
        </p>
      </div>
    </div>
  );
}

interface FieldProps {
  id: string;
  label: string;
  icon: React.ComponentType<{ size?: number; className?: string }>;
  type: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  required?: boolean;
  disabled?: boolean;
  autoComplete?: string;
}

function Field({
  id,
  label,
  icon: Icon,
  type,
  value,
  onChange,
  placeholder,
  required,
  disabled,
  autoComplete,
}: FieldProps) {
  return (
    <label htmlFor={id} className="flex flex-col gap-1 text-xs text-ink-subtle">
      <span className="flex items-center gap-1.5 font-medium">
        <Icon size={12} className="text-ink-subtle" /> {label}
      </span>
      <input
        id={id}
        type={type}
        autoComplete={autoComplete}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        required={required}
        disabled={disabled}
        className="input-sm w-full"
      />
    </label>
  );
}

interface PwProps {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  show: boolean;
  onToggleShow: () => void;
  disabled?: boolean;
}

function PasswordField({
  id,
  label,
  value,
  onChange,
  show,
  onToggleShow,
  disabled,
}: PwProps) {
  return (
    <label htmlFor={id} className="flex flex-col gap-1 text-xs text-ink-subtle">
      <span className="flex items-center gap-1.5 font-medium">
        <KeyRound size={12} className="text-ink-subtle" /> {label}
      </span>
      <div className="relative">
        <input
          id={id}
          type={show ? 'text' : 'password'}
          autoComplete="new-password"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          required
          disabled={disabled}
          className="input-sm w-full pr-9"
        />
        <button
          type="button"
          aria-label={show ? 'nascondi password' : 'mostra password'}
          onClick={onToggleShow}
          disabled={disabled}
          className="absolute right-2 top-1/2 -translate-y-1/2 text-ink-subtle hover:text-ink disabled:opacity-50"
        >
          {show ? <EyeOff size={14} /> : <Eye size={14} />}
        </button>
      </div>
    </label>
  );
}
