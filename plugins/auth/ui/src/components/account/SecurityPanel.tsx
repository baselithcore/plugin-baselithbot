/** Security tab: change password, MFA management, and passkeys. */

import { useState, type FormEvent } from 'react';
import { ShieldCheck, ShieldOff, KeyRound } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../hooks/useAuthContext';
import { changePassword, disableMfaSelf, type Account } from '../../api/account';
import MfaSecurityModal from '../security/MfaSecurityModal';
import PasskeysPanel from './PasskeysPanel';

export default function SecurityPanel({
  account,
  onChange,
}: {
  account: Account | null;
  onChange: () => void;
}) {
  const { t } = useTranslation();
  const { accessToken, refreshAuth } = useAuth();
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState('');
  const [error, setError] = useState('');
  const [mfaOpen, setMfaOpen] = useState(false);
  const [disableCode, setDisableCode] = useState('');
  const [disabling, setDisabling] = useState(false);

  const submitPassword = async (e: FormEvent) => {
    e.preventDefault();
    setMsg('');
    setError('');
    if (next !== confirm) {
      setError(t('account.security.mismatch'));
      return;
    }
    if (!accessToken) return;
    setBusy(true);
    try {
      await changePassword(accessToken, current, next);
      setMsg(t('account.security.passwordChanged'));
      setCurrent('');
      setNext('');
      setConfirm('');
    } catch (err) {
      setError(err instanceof Error ? err.message : t('account.error'));
    } finally {
      setBusy(false);
    }
  };

  const doDisableMfa = async () => {
    if (!accessToken) return;
    setDisabling(true);
    setError('');
    try {
      await disableMfaSelf(accessToken, disableCode.trim());
      setDisableCode('');
      await refreshAuth();
      onChange();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('account.error'));
    } finally {
      setDisabling(false);
    }
  };

  return (
    <section className="acct-card">
      <h2 className="acct-card-title">{t('account.tabs.security')}</h2>
      {msg && <div className="acct-alert acct-alert-ok">{msg}</div>}
      {error && <div className="acct-alert acct-alert-error">{error}</div>}

      {/* Change password */}
      <div className="acct-subsection">
        <h3 className="acct-subtitle">
          <KeyRound size={16} /> {t('account.security.changePassword')}
        </h3>
        <form onSubmit={submitPassword} className="acct-form">
          <label className="acct-label">
            {t('account.security.current')}
            <input
              type="password"
              className="acct-input"
              autoComplete="current-password"
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
              required
            />
          </label>
          <label className="acct-label">
            {t('account.security.new')}
            <input
              type="password"
              className="acct-input"
              autoComplete="new-password"
              minLength={8}
              value={next}
              onChange={(e) => setNext(e.target.value)}
              required
            />
          </label>
          <label className="acct-label">
            {t('account.security.confirm')}
            <input
              type="password"
              className="acct-input"
              autoComplete="new-password"
              minLength={8}
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
            />
          </label>
          <button type="submit" className="acct-btn acct-btn-primary" disabled={busy}>
            {busy ? t('account.saving') : t('account.security.updatePassword')}
          </button>
        </form>
      </div>

      {/* MFA */}
      <div className="acct-subsection">
        <div className="acct-subsection-head">
          <div>
            <h3 className="acct-subtitle">
              {account?.mfa_enabled ? <ShieldCheck size={16} /> : <ShieldOff size={16} />}{' '}
              {t('account.security.mfa')}
            </h3>
            <p className="acct-hint">
              {account?.mfa_enabled ? t('account.security.mfaOn') : t('account.security.mfaOff')}
            </p>
          </div>
          {!account?.mfa_enabled && (
            <button className="acct-btn acct-btn-secondary" onClick={() => setMfaOpen(true)}>
              {t('account.security.enableMfa')}
            </button>
          )}
        </div>
        {account?.mfa_enabled && (
          <div className="acct-inline-form">
            <input
              className="acct-input"
              inputMode="numeric"
              placeholder={t('account.security.mfaCode')}
              value={disableCode}
              onChange={(e) => setDisableCode(e.target.value)}
              maxLength={10}
            />
            <button
              className="acct-btn acct-btn-danger"
              onClick={doDisableMfa}
              disabled={disabling || !disableCode}
            >
              {t('account.security.disableMfa')}
            </button>
          </div>
        )}
      </div>

      {/* Passkeys */}
      <PasskeysPanel onChange={onChange} />

      {mfaOpen && (
        <MfaSecurityModal
          onClose={() => {
            setMfaOpen(false);
            onChange();
          }}
        />
      )}
    </section>
  );
}
