/**
 * AcceptInvite — landing per URL emessi dal maintainer
 * (``/setup/invite?token=…``).
 *
 * Flow:
 *   1. legge ``token`` dalla query string.
 *   2. ``GET /auth/invite/{token}`` → InvitePeek. Email pre-popolata,
 *      reason mostrato se invalido (expired/used/unknown).
 *   3. submit → ``POST /auth/invite/accept`` con {token, password,
 *      display_name}. Login implicito + cookie refresh.
 *   4. ``onComplete`` → App rimonta, AuthContext refresh, viene
 *      mostrato SetupWizard / dashboard.
 *
 * Best practice 2026:
 * - Email server-side (non modificabile dall'utente).
 * - Password min 12 char, conferma, toggle show/hide.
 * - URL token rimosso dalla query post-success (privacy → no leak in
 *   shared screenshot della history).
 */

import { useEffect, useId, useState, type FormEvent } from 'react';
import { Eye, EyeOff, KeyRound, Mail, ShieldCheck, User } from 'lucide-react';

import * as authApi from '../lib/api/auth';
import type { InvitePeek } from '../lib/api/auth';
import { useAuth } from '../contexts/AuthContext';
import { Button } from './ui/Button';

const PASSWORD_MIN = 12;

interface Props {
  token: string;
  onComplete: () => void;
  onCancel: () => void;
}

export function AcceptInvite({ token, onComplete, onCancel }: Props) {
  const [peek, setPeek] = useState<InvitePeek | null>(null);
  const [checking, setChecking] = useState(true);
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { refreshUser } = useAuth();

  const pwId = useId();
  const confirmId = useId();
  const nameId = useId();

  useEffect(() => {
    const ac = new AbortController();
    authApi
      .peekInvite(token, ac.signal)
      .then((r) => {
        setPeek(r);
        if (r.valid && r.display_name) {
          setDisplayName(r.display_name);
        }
      })
      .catch(() => setPeek({ valid: false, reason: 'unknown' }))
      .finally(() => setChecking(false));
    return () => ac.abort();
  }, [token]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
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
      await authApi.acceptInvite({
        token,
        password,
        display_name: displayName.trim(),
      });
      await refreshUser();
      // Rimuovi token dalla query string per pulizia / privacy.
      window.history.replaceState({}, '', '/');
      onComplete();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Errore durante accept.');
    } finally {
      setBusy(false);
    }
  };

  if (checking) {
    return <div className="h-screen w-screen bg-canvas" aria-hidden="true" />;
  }

  if (!peek?.valid) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-canvas px-4">
        <div className="w-full max-w-md rounded-2xl border border-[var(--color-border)] bg-[var(--color-canvas-raised)] p-8 text-center">
          <ShieldCheck size={32} className="mx-auto text-red-400" />
          <h1 className="mt-2 text-lg font-semibold text-ink">Invito non valido</h1>
          <p className="mt-2 text-xs text-ink-subtle">
            {peek?.reason === 'expired' && 'Questo invito è scaduto.'}
            {peek?.reason === 'used' && 'Questo invito è già stato utilizzato.'}
            {(!peek?.reason || peek?.reason === 'unknown') &&
              'Token sconosciuto o malformato.'}
          </p>
          <p className="mt-2 text-[11px] text-ink-subtle">
            Contatta il maintainer per un nuovo invito.
          </p>
          <Button variant="secondary" className="mt-5" onClick={onCancel}>
            Torna al login
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas px-4 py-10">
      <div className="w-full max-w-md rounded-2xl border border-[var(--color-border)] bg-[var(--color-canvas-raised)] p-8 shadow-xl">
        <header className="mb-6 flex flex-col items-center gap-2 text-center">
          <ShieldCheck size={32} className="text-[var(--color-brand)]" />
          <h1 className="text-lg font-semibold text-ink">
            Accetta invito {peek.role_slug ? `(${peek.role_slug})` : ''}
          </h1>
          <p className="text-xs text-ink-subtle">
            Imposta una password per attivare il tuo account.
          </p>
        </header>

        <form onSubmit={submit} className="flex flex-col gap-3">
          <label className="flex flex-col gap-1 text-xs text-ink-subtle">
            <span className="flex items-center gap-1.5 font-medium">
              <Mail size={12} className="text-ink-subtle" /> Email
            </span>
            <input
              type="email"
              value={peek.email ?? ''}
              disabled
              className="input-sm w-full opacity-70"
              aria-label="email (fissata dall'invito)"
            />
          </label>

          <label
            htmlFor={nameId}
            className="flex flex-col gap-1 text-xs text-ink-subtle"
          >
            <span className="flex items-center gap-1.5 font-medium">
              <User size={12} className="text-ink-subtle" /> Nome visualizzato
            </span>
            <input
              id={nameId}
              type="text"
              autoComplete="name"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Mario Rossi"
              className="input-sm w-full"
              disabled={busy}
            />
          </label>

          <label
            htmlFor={pwId}
            className="flex flex-col gap-1 text-xs text-ink-subtle"
          >
            <span className="flex items-center gap-1.5 font-medium">
              <KeyRound size={12} className="text-ink-subtle" /> Password (min{' '}
              {PASSWORD_MIN} caratteri)
            </span>
            <div className="relative">
              <input
                id={pwId}
                type={showPw ? 'text' : 'password'}
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={busy}
                className="input-sm w-full pr-9"
              />
              <button
                type="button"
                aria-label={showPw ? 'nascondi password' : 'mostra password'}
                onClick={() => setShowPw((v) => !v)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-ink-subtle hover:text-ink"
              >
                {showPw ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
          </label>

          <label
            htmlFor={confirmId}
            className="flex flex-col gap-1 text-xs text-ink-subtle"
          >
            <span className="flex items-center gap-1.5 font-medium">
              <KeyRound size={12} className="text-ink-subtle" /> Conferma password
            </span>
            <input
              id={confirmId}
              type={showPw ? 'text' : 'password'}
              autoComplete="new-password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
              disabled={busy}
              className="input-sm w-full"
            />
          </label>

          {error && (
            <p
              role="alert"
              className="rounded border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400"
            >
              {error}
            </p>
          )}

          <Button type="submit" variant="primary" disabled={busy} className="mt-2">
            {busy ? 'Attivazione…' : 'Attiva account'}
          </Button>
        </form>

        <p className="mt-5 text-[10px] text-ink-subtle">
          Invito valido fino a <strong>{peek.expires_at}</strong>.
        </p>
      </div>
    </div>
  );
}
