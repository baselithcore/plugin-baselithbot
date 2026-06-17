/** Passkey enrollment/management (used inside the Security tab). */

import { useCallback, useEffect, useState } from 'react';
import { Fingerprint, Trash2, Plus } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../hooks/useAuthContext';
import {
  listPasskeys,
  registerPasskey,
  deletePasskey,
  isPasskeySupported,
  type PasskeyInfo,
} from '../../api/webauthn';

export default function PasskeysPanel({ onChange }: { onChange?: () => void }) {
  const { t } = useTranslation();
  const { accessToken } = useAuth();
  const [keys, setKeys] = useState<PasskeyInfo[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(() => {
    if (!accessToken) return;
    listPasskeys(accessToken)
      .then(setKeys)
      .catch(() => setKeys([]));
  }, [accessToken]);

  useEffect(load, [load]);

  const add = async () => {
    if (!accessToken) return;
    const name = window.prompt(t('account.passkeys.namePrompt'), t('account.passkeys.defaultName'));
    if (name === null) return;
    setBusy(true);
    setError('');
    try {
      await registerPasskey(name || t('account.passkeys.defaultName'), accessToken);
      load();
      onChange?.();
    } catch (err) {
      const m = err instanceof Error ? err.message : t('account.error');
      if (!/cancel|abort|not allowed/i.test(m)) setError(m);
    } finally {
      setBusy(false);
    }
  };

  const remove = async (id: string) => {
    if (!accessToken || !window.confirm(t('account.passkeys.confirmDelete'))) return;
    try {
      await deletePasskey(id, accessToken);
      load();
      onChange?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('account.error'));
    }
  };

  return (
    <div className="acct-subsection">
      <div className="acct-subsection-head">
        <div>
          <h3 className="acct-subtitle">
            <Fingerprint size={16} /> {t('account.passkeys.title')}
          </h3>
          <p className="acct-hint">{t('account.passkeys.desc')}</p>
        </div>
        {isPasskeySupported() && (
          <button className="acct-btn acct-btn-secondary" onClick={add} disabled={busy}>
            <Plus size={14} /> {t('account.passkeys.add')}
          </button>
        )}
      </div>
      {error && <div className="acct-alert acct-alert-error">{error}</div>}
      {keys.length === 0 ? (
        <p className="acct-empty">{t('account.passkeys.none')}</p>
      ) : (
        <ul className="acct-list">
          {keys.map((k) => (
            <li key={k.id} className="acct-list-row">
              <div>
                <strong>{k.name}</strong>
                <span className="acct-meta">
                  {k.last_used
                    ? t('account.passkeys.lastUsed', {
                        date: new Date(k.last_used).toLocaleString(),
                      })
                    : t('account.passkeys.neverUsed')}
                </span>
              </div>
              <button
                className="acct-icon-btn"
                onClick={() => remove(k.id)}
                aria-label={t('account.passkeys.delete')}
              >
                <Trash2 size={15} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
