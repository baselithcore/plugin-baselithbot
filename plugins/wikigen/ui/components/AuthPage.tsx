/**
 * AuthPage (Fase 6).
 *
 * Login + Register in single mounted component (toggle tab). Mostrata
 * da App.tsx quando `auth.user === null` e Postgres+auth richiesti.
 *
 * Design: minimal, brand-aware via DomainContext (logo + label).
 * Validazione client-side leggera (email shape + password ≥12 char per
 * registrazione — allineato alla regola backend Pydantic).
 *
 * AUTH_PUBLIC_REGISTRATION lato server decide se /register è pubblico
 * o admin-only: in caso admin-only, l'invio register risponde 401/403
 * e il form mostra l'errore.
 */

import { type FormEvent, useState } from 'react';
import {
  ArrowRight,
  BadgeCheck,
  Building2,
  Eye,
  EyeOff,
  KeyRound,
  Lock,
  LogIn,
  Mail,
  ShieldCheck,
  User,
  UserPlus,
} from 'lucide-react';

import { Button } from './ui/Button';
import { Field, InfoPill, PasswordMeter, TabButton } from './auth/AuthAtoms';
import { useAuth } from '../contexts/AuthContext';
import { useDomain } from '../contexts/DomainContext';
import { ApiError } from '../lib/api/client';

type Mode = 'login' | 'register';

export function AuthPage() {
  const { login, register, loading } = useAuth();
  const { branding } = useDomain();
  const [mode, setMode] = useState<Mode>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [tenantName, setTenantName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);

  const isLogin = mode === 'login';
  const hasEmailShape = /^\S+@\S+\.\S+$/.test(email.trim());
  const passwordTooShort = !isLogin && password.length > 0 && password.length < 12;
  const passwordScore = !isLogin
    ? [
        password.length >= 12,
        /[A-Za-zÀ-ÿ]/.test(password),
        /[0-9]|[^A-Za-zÀ-ÿ0-9]/.test(password),
      ].filter(Boolean).length
    : 0;
  const canSubmit =
    !loading &&
    hasEmailShape &&
    password.length >= (isLogin ? 1 : 12) &&
    !passwordTooShort;
  const logoUrl = branding?.logo_url || undefined;
  const appName = branding?.label || branding?.ui?.app_name || 'Wiki';
  const tenantDisplayName = branding?.tenant?.name || branding?.domain || 'tenant';
  const formTitle = isLogin ? 'Accedi' : 'Crea accesso';
  const formSubtitle = isLogin
    ? 'Credenziali del tenant'
    : 'Profilo utente e workspace';

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    if (!canSubmit) return;
    const trimmedEmail = email.trim();
    try {
      if (mode === 'login') {
        await login(trimmedEmail, password);
      } else {
        await register({
          email: trimmedEmail,
          password,
          display_name: displayName.trim(),
          tenant_name: tenantName.trim() || displayName.trim() || trimmedEmail,
        });
      }
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 401) setError('Credenziali non valide.');
        else if (err.status === 403)
          setError(
            'Registrazione disabilitata. Contatta un amministratore per ricevere un invito.'
          );
        else if (err.status === 409) setError('Email già registrata.');
        else if (err.status === 429) setError('Troppi tentativi. Riprova fra poco.');
        else setError(err.message || `Errore (${err.status}).`);
      } else {
        setError(err instanceof Error ? err.message : 'Errore sconosciuto.');
      }
    }
  };

  return (
    <div className="min-h-screen bg-[var(--color-canvas)] px-4 py-6 sm:px-6 lg:grid lg:place-items-center">
      <div className="mx-auto grid w-full max-w-5xl overflow-hidden rounded-lg border border-[var(--color-border)] bg-[var(--color-canvas-raised)] shadow-lg lg:min-h-[36rem] lg:grid-cols-[1.05fr_0.95fr]">
        <section className="flex min-h-[13rem] flex-col justify-between border-b border-[var(--color-border)] bg-[var(--color-surface)] p-5 sm:p-7 lg:border-b-0 lg:border-r">
          <div className="flex items-start gap-3">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden rounded-lg border border-[var(--color-border)] bg-[var(--color-canvas-raised)] text-[var(--color-brand)] shadow-xs">
              {logoUrl ? (
                <img
                  src={logoUrl}
                  alt=""
                  width={48}
                  height={48}
                  className="h-full w-full object-contain p-1.5"
                />
              ) : (
                <Lock size={21} aria-hidden />
              )}
            </div>
            <div className="min-w-0 pt-0.5">
              <p className="section-label">Sistema</p>
              <h1 className="truncate text-lg font-semibold text-ink">{appName}</h1>
              {branding?.description && (
                <p className="mt-2 max-w-md text-sm leading-6 text-ink-muted">
                  {branding.description}
                </p>
              )}
            </div>
          </div>

          <div className="mt-8 grid gap-2 sm:grid-cols-3 lg:grid-cols-1 xl:grid-cols-3">
            <InfoPill icon={Building2} label="Tenant" value={tenantDisplayName} />
            <InfoPill icon={ShieldCheck} label="Sessione" value="Protetta" />
            <InfoPill icon={BadgeCheck} label="Accesso" value="Riservato" />
          </div>
        </section>

        <section className="flex items-center p-5 sm:p-7">
          <div className="w-full">
            <div className="mb-5">
              <p className="section-label">Accesso tenant</p>
              <h2 className="mt-1 text-xl font-semibold text-ink">{formTitle}</h2>
              <p className="mt-1 text-sm text-ink-muted">{formSubtitle}</p>
            </div>

            <div
              className="mb-5 grid grid-cols-2 gap-1 rounded-lg border border-[var(--color-border)] bg-[var(--color-canvas)] p-1 text-xs"
              role="tablist"
              aria-label="modalità accesso"
            >
              <TabButton
                active={isLogin}
                icon={LogIn}
                label="Login"
                onClick={() => {
                  setMode('login');
                  setError(null);
                }}
              />
              <TabButton
                active={!isLogin}
                icon={UserPlus}
                label="Registrazione"
                onClick={() => {
                  setMode('register');
                  setError(null);
                }}
              />
            </div>

            <form onSubmit={submit} className="space-y-4" noValidate>
              <Field
                label="Email"
                type="email"
                value={email}
                onChange={setEmail}
                autoComplete="email"
                inputMode="email"
                required
                autoFocus
                icon={Mail}
                placeholder="nome@azienda.it"
                error={
                  email.length > 0 && !hasEmailShape
                    ? 'Inserisci un indirizzo email valido.'
                    : undefined
                }
              />
              <Field
                label="Password"
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={setPassword}
                autoComplete={isLogin ? 'current-password' : 'new-password'}
                required
                icon={KeyRound}
                hint={!isLogin ? 'Minimo 12 caratteri.' : undefined}
                placeholder={isLogin ? 'Inserisci la password' : 'Crea una password sicura'}
                error={passwordTooShort ? 'Minimo 12 caratteri.' : undefined}
                trailing={
                  <button
                    type="button"
                    onClick={() => setShowPassword((v) => !v)}
                    className="focus-ring inline-flex size-8 items-center justify-center rounded-lg border border-transparent text-ink-subtle transition-colors hover:border-[var(--color-border)] hover:bg-[var(--color-surface)] hover:text-ink"
                    aria-label={showPassword ? 'nascondi password' : 'mostra password'}
                  >
                    {showPassword ? (
                      <EyeOff size={14} aria-hidden />
                    ) : (
                      <Eye size={14} aria-hidden />
                    )}
                  </button>
                }
              />
              {!isLogin && <PasswordMeter score={passwordScore} />}
              {!isLogin && (
                <>
                  <Field
                    label="Nome visualizzato"
                    value={displayName}
                    onChange={setDisplayName}
                    autoComplete="name"
                    icon={User}
                    placeholder="Mario Rossi"
                  />
                  <Field
                    label="Workspace"
                    value={tenantName}
                    onChange={setTenantName}
                    autoComplete="organization"
                    icon={Building2}
                    hint="Opzionale, se vuoto usa nome o email."
                    placeholder="Area Sinistri"
                  />
                </>
              )}

              {error && (
                <div
                  role="alert"
                  aria-live="polite"
                  className="rounded-md border border-[var(--color-danger)]/40 bg-[var(--color-danger)]/10 px-3 py-2 text-xs text-[var(--color-danger)]"
                >
                  {error}
                </div>
              )}

              <Button
                type="submit"
                variant="primary"
                size="md"
                loading={loading}
                disabled={!canSubmit}
                leadingIcon={isLogin ? LogIn : UserPlus}
                trailingIcon={ArrowRight}
                className="min-h-11 w-full justify-center rounded-lg text-sm shadow-sm transition-all hover:shadow-md disabled:border disabled:border-[var(--color-border)] disabled:bg-[var(--color-surface-hover)] disabled:text-ink-subtle disabled:opacity-100 disabled:shadow-none"
              >
                {isLogin ? 'Accedi' : 'Crea workspace'}
              </Button>
            </form>
          </div>
        </section>
      </div>
    </div>
  );
}
