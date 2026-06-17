/** Reset-password page: consumes the one-time token from the URL. */

import { useMemo, useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { resetPassword } from '../../api/recovery';
import AuthShell from './AuthShell';

function tokenFromUrl(): string {
  return new URLSearchParams(window.location.search).get('token') || '';
}

export default function ResetPasswordPage() {
  const { t } = useTranslation();
  const token = useMemo(tokenFromUrl, []);
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState('');

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    if (password !== confirm) {
      setError(t('recovery.passwordsMismatch'));
      return;
    }
    setLoading(true);
    try {
      await resetPassword(token, password);
      setDone(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('recovery.genericError'));
    } finally {
      setLoading(false);
    }
  };

  if (!token) {
    return (
      <AuthShell title={t('recovery.resetTitle')}>
        <div className="auth-form">
          <div className="auth-error">{t('recovery.invalidLink')}</div>
          <a className="auth-button" href="/auth/forgot-password">
            {t('recovery.requestNew')}
          </a>
        </div>
      </AuthShell>
    );
  }

  return (
    <AuthShell title={t('recovery.resetTitle')} subtitle={t('recovery.resetSubtitle')}>
      {done ? (
        <div className="auth-form">
          <div className="auth-success">{t('recovery.resetDone')}</div>
          <a className="auth-button" href="/auth/login">
            {t('recovery.backToLogin')}
          </a>
        </div>
      ) : (
        <form onSubmit={submit} className="auth-form">
          {error && (
            <div className="auth-error">
              <span className="auth-error-icon">⚠️</span>
              {error}
            </div>
          )}
          <div className="auth-field">
            <label htmlFor="pw" className="auth-label">
              {t('recovery.newPassword')}
            </label>
            <input
              id="pw"
              type="password"
              className="auth-input"
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              autoFocus
              minLength={8}
            />
          </div>
          <div className="auth-field">
            <label htmlFor="pw2" className="auth-label">
              {t('recovery.confirmPassword')}
            </label>
            <input
              id="pw2"
              type="password"
              className="auth-input"
              autoComplete="new-password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
              minLength={8}
            />
          </div>
          <button type="submit" className="auth-button" disabled={loading}>
            {loading ? <span className="auth-spinner" /> : t('recovery.resetSubmit')}
          </button>
        </form>
      )}
    </AuthShell>
  );
}
