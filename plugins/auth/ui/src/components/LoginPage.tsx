/**
 * Login Page Component
 *
 * Handles email/password login and MFA verification.
 */

import { useState, type FormEvent } from 'react';
import { useAuth } from '../hooks/useAuthContext';
import '../index.css';

interface AuthLogoProps {
  size?: number;
}

function AuthLogo({ size = 80 }: AuthLogoProps) {
  const scaledSize = size || 64;
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 64 64"
      fill="none"
      width={scaledSize}
      height={scaledSize}
    >
      <defs>
        <linearGradient
          id="hydra_grad"
          x1="0"
          y1="0"
          x2="64"
          y2="64"
          gradientUnits="userSpaceOnUse"
        >
          <stop stopColor="#7ee0ff" />
          <stop offset="1" stopColor="#7c8cff" />
        </linearGradient>
        <filter id="glow" x="-10" y="-10" width="84" height="84" filterUnits="userSpaceOnUse">
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
      </defs>
      {/* Background Shield */}
      <path
        d="M32 4L54 12V30C54 44.4 44.6 57.6 32 62C19.4 57.6 10 44.4 10 30V12L32 4Z"
        fill="#04060f"
        stroke="url(#hydra_grad)"
        strokeWidth="2"
      />

      {/* Central Lock/Shield Hexagon */}
      <path d="M32 18L44 25V39L32 46L20 39V25L32 18Z" fill="url(#hydra_grad)" opacity="0.9">
        <animate attributeName="opacity" values="0.7;1;0.7" dur="3s" repeatCount="indefinite" />
      </path>

      {/* Inner Lock Detail */}
      <circle cx="32" cy="30" r="3" fill="#04060f" />
      <rect x="30" y="32" width="4" height="6" rx="1" fill="#04060f" />
    </svg>
  );
}

interface LoginPageProps {
  onSuccess?: () => void;
}

export default function LoginPage({ onSuccess }: LoginPageProps) {
  const {
    login,
    logout,
    verifyMFA,
    isLoading,
    error: authError,
    mfaRequired,
    mfaTempToken,
  } = useAuth();

  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [mfaCode, setMfaCode] = useState('');
  const [localError, setLocalError] = useState('');

  const displayError = localError || authError;

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault();
    setLocalError('');

    try {
      const result = await login(identifier, password);
      if (!result.mfaRequired) {
        onSuccess?.();
      }
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : 'Login failed');
    }
  };

  const handleMFAVerify = async (e: FormEvent) => {
    e.preventDefault();
    setLocalError('');

    if (!mfaTempToken) {
      setLocalError('Missing MFA token');
      return;
    }

    try {
      await verifyMFA(mfaTempToken, mfaCode);
      onSuccess?.();
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : 'MFA verification failed');
    }
  };

  if (mfaRequired) {
    return (
      <div className="auth-page">
        <div className="auth-card">
          <div className="auth-header">
            <h1 className="auth-title">Two-Factor Authentication</h1>
            <p className="auth-subtitle">Enter the code from your authenticator app</p>
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
                Verification Code
              </label>
              <input
                id="mfaCode"
                type="text"
                inputMode="numeric"
                pattern="[0-9A-Za-z\-]*"
                autoComplete="one-time-code"
                placeholder="000000"
                value={mfaCode}
                onChange={(e) => setMfaCode(e.target.value)}
                className="auth-input auth-input-code"
                maxLength={10}
                required
                autoFocus
              />
              <p className="auth-hint">Enter your 6-digit code or a backup code</p>
            </div>

            <button type="submit" className="auth-button" disabled={isLoading}>
              {isLoading ? <span className="auth-spinner" /> : 'Verify'}
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
              ← Back to login
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-header">
          <div className="auth-logo">
            <AuthLogo size={80} />
          </div>
          <h1 className="auth-title baselith-brand">
            BaselithAuth<span className="baselith-brand-dot">.</span>
          </h1>
          <p className="auth-subtitle">Sign in to access the system</p>
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
              Email or Username
            </label>
            <input
              id="identifier"
              type="text"
              autoComplete="username"
              placeholder="you@example.com or username"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              className="auth-input"
              required
              autoFocus
            />
          </div>

          <div className="auth-field">
            <label htmlFor="password" className="auth-label">
              Password
            </label>
            <input
              id="password"
              type="password"
              autoComplete="current-password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="auth-input"
              required
            />
          </div>

          <button type="submit" className="auth-button" disabled={isLoading}>
            {isLoading ? <span className="auth-spinner" /> : 'Sign In'}
          </button>
        </form>
      </div>

      <p className="auth-footer">© 2026 Gippo. All rights reserved.</p>
    </div>
  );
}
