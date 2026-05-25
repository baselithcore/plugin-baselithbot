/**
 * ForcePasswordChange — gate mostrato dopo login se
 * ``user.must_change_password === true`` (NIST SP 800-63B).
 *
 * Backend rifiuta tutti gli endpoint protetti con 403 finché la
 * password non viene cambiata via ``POST /auth/password``. Frontend
 * fa lo stesso a livello UX: occupa il viewport con il form fino a
 * che il flag non si abbassa.
 */

import { useId, useState, type FormEvent } from 'react';
import { Eye, EyeOff, KeyRound, ShieldAlert } from 'lucide-react';

import { useAuth } from '../contexts/AuthContext';
import * as authApi from '../lib/api/auth';
import { Button } from './ui/Button';

const PASSWORD_MIN = 12;

interface Props {
  onComplete: () => void;
}

export function ForcePasswordChange({ onComplete }: Props) {
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { logout } = useAuth();

  const curId = useId();
  const newId = useId();
  const confirmId = useId();

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (next.length < PASSWORD_MIN) {
      setError(`Password deve essere di almeno ${PASSWORD_MIN} caratteri.`);
      return;
    }
    if (next === current) {
      setError('La nuova password deve essere diversa dalla precedente.');
      return;
    }
    if (next !== confirm) {
      setError('Le password non coincidono.');
      return;
    }
    setBusy(true);
    try {
      // /auth/password richiede require_user (NON force-change) →
      // questo endpoint resta accessibile durante il "must-change"
      // hold. Backend azzera flag + revoca tutti i refresh token.
      await authApi.changePassword({
        current_password: current,
        new_password: next,
      });
      // Refresh revocato server-side → re-login obbligatorio. Logout
      // pulisce lo stato AuthContext e App rimonta a AuthPage.
      await logout();
      onComplete();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Errore cambio password.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-canvas px-4 py-10">
      <div className="w-full max-w-md rounded-2xl border border-[var(--color-border)] bg-[var(--color-canvas-raised)] p-8 shadow-xl">
        <header className="mb-6 flex flex-col items-center gap-2 text-center">
          <ShieldAlert size={32} className="text-[var(--color-brand)]" />
          <h1 className="text-lg font-semibold text-ink">Cambio password obbligatorio</h1>
          <p className="text-xs text-ink-subtle">
            Per la sicurezza dell'account, devi impostare una nuova password prima di proseguire.
          </p>
        </header>

        <form onSubmit={submit} className="flex flex-col gap-3">
          <PwField
            id={curId}
            label="Password attuale"
            value={current}
            onChange={setCurrent}
            show={showPw}
            onToggleShow={() => setShowPw((v) => !v)}
            disabled={busy}
            autoComplete="current-password"
          />
          <PwField
            id={newId}
            label={`Nuova password (min ${PASSWORD_MIN} caratteri)`}
            value={next}
            onChange={setNext}
            show={showPw}
            onToggleShow={() => setShowPw((v) => !v)}
            disabled={busy}
            autoComplete="new-password"
          />
          <PwField
            id={confirmId}
            label="Conferma nuova password"
            value={confirm}
            onChange={setConfirm}
            show={showPw}
            onToggleShow={() => setShowPw((v) => !v)}
            disabled={busy}
            autoComplete="new-password"
          />

          {error && (
            <p
              role="alert"
              className="rounded border border-red-500/30 bg-red-500/10 px-3 py-2 text-xs text-red-400"
            >
              {error}
            </p>
          )}

          <Button type="submit" variant="primary" disabled={busy} className="mt-2">
            {busy ? 'Aggiornamento…' : 'Cambia password e prosegui'}
          </Button>
          <button
            type="button"
            onClick={() => logout()}
            disabled={busy}
            className="text-[11px] text-ink-subtle hover:text-ink disabled:opacity-50"
          >
            Logout
          </button>
        </form>
      </div>
    </div>
  );
}

interface PwFieldProps {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  show: boolean;
  onToggleShow: () => void;
  disabled?: boolean;
  autoComplete: string;
}

function PwField({
  id,
  label,
  value,
  onChange,
  show,
  onToggleShow,
  disabled,
  autoComplete,
}: PwFieldProps) {
  return (
    <label htmlFor={id} className="flex flex-col gap-1 text-xs text-ink-subtle">
      <span className="flex items-center gap-1.5 font-medium">
        <KeyRound size={12} className="text-ink-subtle" /> {label}
      </span>
      <div className="relative">
        <input
          id={id}
          type={show ? 'text' : 'password'}
          autoComplete={autoComplete}
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
