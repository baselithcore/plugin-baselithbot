/** Invitation acceptance page: prefilled email, user sets username + password. */

import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { acceptInvitation, getInvitation, type InviteInfo } from '../../api/recovery';
import AuthShell from './AuthShell';

function tokenFromUrl(): string {
  return new URLSearchParams(window.location.search).get('token') || '';
}

export default function AcceptInvitePage() {
  const { t } = useTranslation();
  const token = useMemo(tokenFromUrl, []);
  const [invite, setInvite] = useState<InviteInfo | null>(null);
  const [loadError, setLoadError] = useState('');
  const [fullName, setFullName] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!token) {
      setLoadError(t('recovery.invalidLink'));
      return;
    }
    getInvitation(token)
      .then(setInvite)
      .catch((err) =>
        setLoadError(err instanceof Error ? err.message : t('recovery.genericError'))
      );
  }, [token, t]);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    if (password !== confirm) {
      setError(t('recovery.passwordsMismatch'));
      return;
    }
    setLoading(true);
    try {
      await acceptInvitation({
        token,
        password,
        username: username || undefined,
        full_name: fullName || undefined,
      });
      setDone(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('recovery.genericError'));
    } finally {
      setLoading(false);
    }
  };

  if (loadError) {
    return (
      <AuthShell title={t('recovery.inviteTitle')}>
        <div className="auth-form">
          <div className="auth-error">{loadError}</div>
        </div>
      </AuthShell>
    );
  }

  return (
    <AuthShell
      title={t('recovery.inviteTitle')}
      subtitle={invite ? t('recovery.inviteSubtitle', { email: invite.email }) : ''}
    >
      {done ? (
        <div className="auth-form">
          <div className="auth-success">{t('recovery.inviteDone')}</div>
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
            <label htmlFor="fn" className="auth-label">
              {t('recovery.fullName')}
            </label>
            <input
              id="fn"
              type="text"
              className="auth-input"
              autoComplete="name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
          </div>
          <div className="auth-field">
            <label htmlFor="un" className="auth-label">
              {t('recovery.usernameOptional')}
            </label>
            <input
              id="un"
              type="text"
              className="auth-input"
              autoComplete="username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>
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
          <button type="submit" className="auth-button" disabled={loading || !invite}>
            {loading ? <span className="auth-spinner" /> : t('recovery.createAccount')}
          </button>
        </form>
      )}
    </AuthShell>
  );
}
