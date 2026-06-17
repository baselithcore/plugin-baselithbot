/** Forgot-password request page (enumeration-safe). */

import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { forgotPassword } from '../../api/recovery';
import AuthShell from './AuthShell';

export default function ForgotPasswordPage() {
  const { t } = useTranslation();
  const [identifier, setIdentifier] = useState('');
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState('');

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');
    try {
      await forgotPassword(identifier);
      setDone(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('recovery.genericError'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <AuthShell title={t('recovery.forgotTitle')} subtitle={t('recovery.forgotSubtitle')}>
      {done ? (
        <div className="auth-form">
          <div className="auth-success">{t('recovery.checkInbox')}</div>
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
            <label htmlFor="identifier" className="auth-label">
              {t('recovery.identifier')}
            </label>
            <input
              id="identifier"
              type="text"
              className="auth-input"
              autoComplete="username"
              placeholder={t('recovery.identifierPlaceholder')}
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              required
              autoFocus
            />
          </div>
          <button type="submit" className="auth-button" disabled={loading}>
            {loading ? <span className="auth-spinner" /> : t('recovery.sendLink')}
          </button>
          <a className="auth-link" href="/auth/login">
            ← {t('recovery.backToLogin')}
          </a>
        </form>
      )}
    </AuthShell>
  );
}
