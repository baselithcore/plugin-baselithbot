import { useEffect, useState, type FormEvent } from 'react';
import { Lock, Mail, ShieldCheck, User } from 'lucide-react';
import { api } from '../lib/api.js';
import { setSession } from '../lib/auth.js';

interface Props {
  onAuthenticated: () => void;
}

type Mode = 'login' | 'register';

export function LoginPage({ onAuthenticated }: Props) {
  const [mode, setMode] = useState<Mode>('login');
  const [registrationEnabled, setRegistrationEnabled] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let alive = true;
    api
      .authConfig()
      .then((cfg) => {
        if (alive) setRegistrationEnabled(cfg.registrationEnabled);
      })
      .catch(() => {
        if (alive) setRegistrationEnabled(false);
      });
    return () => {
      alive = false;
    };
  }, []);

  function switchMode(next: Mode): void {
    setMode(next);
    setError(null);
  }

  async function handleSubmit(e: FormEvent): Promise<void> {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const res =
        mode === 'login'
          ? await api.login({ email, password })
          : await api.register({
              email,
              password,
              ...(displayName.trim() ? { displayName: displayName.trim() } : {}),
            });
      setSession(res.accessToken, res.user);
      onAuthenticated();
    } catch (err) {
      const message =
        err instanceof Error
          ? err.message
          : mode === 'login'
            ? 'Sign-in failed.'
            : 'Sign-up failed.';
      setError(message);
    } finally {
      setSubmitting(false);
    }
  }

  const isRegister = mode === 'register';
  const minPassword = isRegister ? 12 : 1;
  const canSubmit = !submitting && email.length > 0 && password.length >= minPassword;

  return (
    <div className="h-screen w-screen flex items-center justify-center bg-surface-0 text-text">
      <form
        onSubmit={handleSubmit}
        className="panel w-full max-w-sm p-6 flex flex-col gap-4"
        aria-label={isRegister ? 'Create account' : 'Sign in'}
      >
        <header className="flex flex-col items-center gap-2 pb-2">
          <ShieldCheck className="w-7 h-7 text-accent" aria-hidden />
          <h1 className="text-base font-semibold tracking-tight">
            {isRegister ? 'Create your dbview account' : 'Sign in to dbview'}
          </h1>
          <p className="text-xs text-text-muted">
            {isRegister ? 'Pick an email and a strong password.' : 'Use your account credentials.'}
          </p>
        </header>

        {registrationEnabled && (
          <div
            role="tablist"
            aria-label="Authentication mode"
            className="grid grid-cols-2 gap-1 rounded bg-surface-2 p-1 text-xs"
          >
            <button
              type="button"
              role="tab"
              aria-selected={!isRegister}
              onClick={() => switchMode('login')}
              className={`rounded px-2 py-1 transition-colors focus:outline-none focus:ring-2 focus:ring-accent ${
                !isRegister ? 'bg-surface-0 text-text' : 'text-text-muted hover:text-text'
              }`}
            >
              Sign in
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={isRegister}
              onClick={() => switchMode('register')}
              className={`rounded px-2 py-1 transition-colors focus:outline-none focus:ring-2 focus:ring-accent ${
                isRegister ? 'bg-surface-0 text-text' : 'text-text-muted hover:text-text'
              }`}
            >
              Create account
            </button>
          </div>
        )}

        {isRegister && (
          <label className="flex flex-col gap-1 text-xs">
            <span className="text-text-muted">Display name (optional)</span>
            <div className="relative">
              <User
                className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-text-dim"
                aria-hidden
              />
              <input
                type="text"
                autoComplete="name"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                className="input pl-8 w-full"
                placeholder="Jane Doe"
                maxLength={120}
              />
            </div>
          </label>
        )}

        <label className="flex flex-col gap-1 text-xs">
          <span className="text-text-muted">Email</span>
          <div className="relative">
            <Mail
              className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-text-dim"
              aria-hidden
            />
            <input
              type="email"
              required
              autoComplete={isRegister ? 'email' : 'username'}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="input pl-8 w-full"
              placeholder="you@example.com"
            />
          </div>
        </label>

        <label className="flex flex-col gap-1 text-xs">
          <span className="text-text-muted">
            Password{isRegister && <span className="text-text-dim"> (min 12 chars)</span>}
          </span>
          <div className="relative">
            <Lock
              className="absolute left-2 top-1/2 -translate-y-1/2 w-4 h-4 text-text-dim"
              aria-hidden
            />
            <input
              type="password"
              required
              autoComplete={isRegister ? 'new-password' : 'current-password'}
              minLength={minPassword}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input pl-8 w-full"
              placeholder="••••••••"
            />
          </div>
        </label>

        {error && (
          <div
            role="alert"
            className="text-xs text-rose-300 bg-rose-500/10 border border-rose-500/30 rounded px-3 py-2"
          >
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={!canSubmit}
          className="btn btn-primary w-full justify-center"
        >
          {submitting
            ? isRegister
              ? 'Creating account…'
              : 'Signing in…'
            : isRegister
              ? 'Create account'
              : 'Sign in'}
        </button>
      </form>
    </div>
  );
}
