/** Profile tab: display name, username, verification + account status. */

import { useEffect, useState, type FormEvent } from 'react';
import { CheckCircle2, AlertCircle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../hooks/useAuthContext';
import { updateProfile, type Account } from '../../api/account';

export default function ProfilePanel({
  account,
  onChange,
}: {
  account: Account | null;
  onChange: () => void;
}) {
  const { t } = useTranslation();
  const { accessToken } = useAuth();
  const [fullName, setFullName] = useState('');
  const [username, setUsername] = useState('');
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    setFullName(account?.full_name || '');
    setUsername(account?.username || '');
  }, [account]);

  const save = async (e: FormEvent) => {
    e.preventDefault();
    if (!accessToken) return;
    setBusy(true);
    setMsg('');
    setError('');
    try {
      await updateProfile(accessToken, fullName, username);
      setMsg(t('account.profile.saved'));
      onChange();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('account.error'));
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="acct-card">
      <h2 className="acct-card-title">{t('account.tabs.profile')}</h2>
      {msg && <div className="acct-alert acct-alert-ok">{msg}</div>}
      {error && <div className="acct-alert acct-alert-error">{error}</div>}

      <div className="acct-readonly">
        <div className="acct-readonly-row">
          <span>{t('account.profile.email')}</span>
          <strong>
            {account?.email}
            {account?.email_verified ? (
              <span className="acct-badge acct-badge-ok">
                <CheckCircle2 size={12} /> {t('account.profile.verified')}
              </span>
            ) : (
              <span className="acct-badge acct-badge-warn">
                <AlertCircle size={12} /> {t('account.profile.unverified')}
              </span>
            )}
          </strong>
        </div>
        <div className="acct-readonly-row">
          <span>{t('account.profile.roles')}</span>
          <strong>{account?.roles.join(', ') || '—'}</strong>
        </div>
        <div className="acct-readonly-row">
          <span>{t('account.profile.status')}</span>
          <strong className="acct-status">{account?.status || '—'}</strong>
        </div>
      </div>

      <form onSubmit={save} className="acct-form">
        <label className="acct-label">
          {t('account.profile.fullName')}
          <input
            className="acct-input"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            maxLength={160}
          />
        </label>
        <label className="acct-label">
          {t('account.profile.username')}
          <input
            className="acct-input"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            maxLength={50}
          />
        </label>
        <button type="submit" className="acct-btn acct-btn-primary" disabled={busy}>
          {busy ? t('account.saving') : t('account.profile.save')}
        </button>
      </form>
    </section>
  );
}
