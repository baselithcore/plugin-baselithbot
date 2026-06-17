/**
 * Login Page Component
 *
 * Handles email/password login and MFA verification.
 */

import { useEffect, useState, type FormEvent } from 'react';
import { useAuthT } from '../i18n/standalone';
import { useAuth } from '../hooks/useAuthContext';
import { loginWithPasskey, isPasskeySupported } from '../api/webauthn';
import SsoButtons from './SsoButtons';
import AuthLogo from './ui/AuthLogo';
import '../index.css';

interface LoginPageProps {
  onSuccess?: () => void;
}

export default function LoginPage({ onSuccess }: LoginPageProps) {
  const t = useAuthT();
  const {
    login,
    logout,
    verifyMFA,
    refreshAuth,
    isLoading,
    error: authError,
    mfaRequired,
    mfaTempToken,
  } = useAuth();

  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [mfaCode, setMfaCode] = useState('');
  const [localError, setLocalError] = useState('');
  const [passkeyBusy, setPasskeyBusy] = useState(false);

  // Surface an SSO redirect failure passed back as ?sso_error=...
  useEffect(() => {
    const reason = new URLSearchParams(window.location.search).get('sso_error');
    if (reason) setLocalError(t('login.ssoError'));
  }, [t]);

  const displayError = localError || authError;

  const handlePasskeyLogin = async () => {
    setLocalError('');
    setPasskeyBusy(true);
    try {
      await loginWithPasskey();
      await refreshAuth();
      onSuccess?.();
    } catch (err) {
      // A user-cancelled prompt is not an error worth surfacing loudly.
      const msg = err instanceof Error ? err.message : t('login.errors.loginFailed');
      if (!/cancel|abort|not allowed/i.test(msg)) setLocalError(msg);
    } finally {
      setPasskeyBusy(false);
    }
  };

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault();
    setLocalError('');

    try {
      const result = await login(identifier, password);
      if (!result.mfaRequired) {
        onSuccess?.();
      }
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : t('login.errors.loginFailed'));
    }
  };

  const handleMFAVerify = async (e: FormEvent) => {
    e.preventDefault();
    setLocalError('');

    if (!mfaTempToken) {
      setLocalError(t('login.errors.missingMfaToken'));
      return;
    }

    try {
      await verifyMFA(mfaTempToken, mfaCode);
      onSuccess?.();
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : t('login.errors.mfaVerificationFailed'));
    }
  };

  if (mfaRequired) {
    return (
      <div className="auth-page">
        <div className="aurora" aria-hidden="true" />
        <div className="auth-card">
          <div className="auth-header">
            <h1 className="auth-title">{t('login.mfaHeader')}</h1>
            <p className="auth-subtitle">{t('login.mfaHeaderSubtitle')}</p>
          </div>

          <form onSubmit={handleMFAVerify} className="auth-form">
            {displayError && (
              <div className="auth-error">
                <span className="auth-error-icon">⚠️</span>
                {displayError}
              </div>
            )}

            <div className="auth-field">
              <label htmlFor="mfaCode" className="auth-label">
                {t('login.mfaCodeLabel')}
              </label>
              <input
                id="mfaCode"
                type="text"
                inputMode="numeric"
                pattern="[0-9A-Za-z\-]*"
                autoComplete="one-time-code"
                placeholder={t('login.mfaCodePlaceholder')}
                value={mfaCode}
                onChange={(e) => setMfaCode(e.target.value)}
                className="auth-input auth-input-code"
                maxLength={10}
                required
                autoFocus
              />
              <p className="auth-hint">{t('login.mfaCodeHint')}</p>
            </div>

            <button type="submit" className="auth-button" disabled={isLoading}>
              {isLoading ? <span className="auth-spinner" /> : t('login.verify')}
            </button>

            <button
              type="button"
              className="auth-link"
              onClick={() => {
                logout();
                setMfaCode('');
                setLocalError('');
              }}
            >
              ← {t('login.backToLogin')}
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <div className="aurora" aria-hidden="true" />
      <div className="auth-card">
        <div className="auth-header">
          <div className="auth-logo">
            <AuthLogo size={80} />
          </div>
          <h1 className="auth-title baselith-brand">
            BaselithAuth<span className="baselith-brand-dot">.</span>
          </h1>
          <p className="auth-subtitle">{t('login.brandSubtitle')}</p>
        </div>

        <form onSubmit={handleLogin} className="auth-form">
          {displayError && (
            <div className="auth-error">
              <span className="auth-error-icon">⚠️</span>
              {displayError}
            </div>
          )}

          <div className="auth-field">
            <label htmlFor="identifier" className="auth-label">
              {t('login.identifier')}
            </label>
            <input
              id="identifier"
              type="text"
              autoComplete="username"
              placeholder={t('login.identifierPlaceholderCombined')}
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              className="auth-input"
              required
              autoFocus
            />
          </div>

          <div className="auth-field">
            <label htmlFor="password" className="auth-label">
              {t('login.password')}
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              placeholder={t('login.passwordDots')}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="auth-input"
              required
            />
          </div>

          <button type="submit" className="auth-button" disabled={isLoading}>
            {isLoading ? <span className="auth-spinner" /> : t('login.submit')}
          </button>

          {isPasskeySupported() && (
            <>
              <div className="auth-divider">
                <span>{t('login.or')}</span>
              </div>
              <button
                type="button"
                className="auth-button auth-button-secondary"
                onClick={handlePasskeyLogin}
                disabled={passkeyBusy}
              >
                {passkeyBusy ? <span className="auth-spinner" /> : `🔑 ${t('login.passkey')}`}
              </button>
            </>
          )}

          <SsoButtons />

          <a href="/auth/forgot-password" className="auth-link auth-link-muted">
            {t('login.forgotPassword')}
          </a>
        </form>
      </div>

      <p className="auth-footer">{t('login.footer')}</p>
    </div>
  );
}
