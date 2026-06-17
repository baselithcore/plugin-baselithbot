/** Personal access tokens (API keys) tab. */

import { useCallback, useEffect, useState } from 'react';
import { KeyRound, Plus, Trash2, Copy, Check } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../hooks/useAuthContext';
import { listApiKeys, createApiKey, revokeApiKey, type ApiKeyInfo } from '../../api/account';

export default function ApiKeysPanel() {
  const { t } = useTranslation();
  const { accessToken } = useAuth();
  const [keys, setKeys] = useState<ApiKeyInfo[]>([]);
  const [name, setName] = useState('');
  const [expiry, setExpiry] = useState('90');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [created, setCreated] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const load = useCallback(() => {
    if (!accessToken) return;
    listApiKeys(accessToken)
      .then(setKeys)
      .catch(() => setKeys([]));
  }, [accessToken]);

  useEffect(load, [load]);

  const create = async () => {
    if (!accessToken || !name.trim()) return;
    setBusy(true);
    setError('');
    try {
      const days = expiry === 'never' ? null : parseInt(expiry, 10);
      const res = await createApiKey(accessToken, name.trim(), days);
      setCreated(res.key);
      setName('');
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('account.error'));
    } finally {
      setBusy(false);
    }
  };

  const revoke = async (id: string) => {
    if (!accessToken || !window.confirm(t('account.apikeys.confirmRevoke'))) return;
    try {
      await revokeApiKey(accessToken, id);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('account.error'));
    }
  };

  const copy = () => {
    if (created) {
      navigator.clipboard.writeText(created);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    }
  };

  const active = keys.filter((k) => !k.revoked_at);

  return (
    <section className="acct-card">
      <h2 className="acct-card-title">
        <KeyRound size={18} /> {t('account.apikeys.title')}
      </h2>
      <p className="acct-hint">{t('account.apikeys.desc')}</p>
      {error && <div className="acct-alert acct-alert-error">{error}</div>}

      {created && (
        <div className="acct-key-reveal">
          <p className="acct-key-warning">{t('account.apikeys.copyNow')}</p>
          <div className="acct-key-row">
            <code className="acct-key-value">{created}</code>
            <button className="acct-btn acct-btn-secondary" onClick={copy}>
              {copied ? <Check size={14} /> : <Copy size={14} />}{' '}
              {copied ? t('account.apikeys.copied') : t('account.apikeys.copy')}
            </button>
          </div>
          <button className="acct-btn acct-btn-ghost" onClick={() => setCreated(null)}>
            {t('account.apikeys.dismiss')}
          </button>
        </div>
      )}

      <div className="acct-inline-form">
        <input
          className="acct-input"
          placeholder={t('account.apikeys.namePlaceholder')}
          value={name}
          onChange={(e) => setName(e.target.value)}
          maxLength={120}
        />
        <select
          className="acct-input acct-select"
          value={expiry}
          onChange={(e) => setExpiry(e.target.value)}
        >
          <option value="30">30 {t('account.apikeys.days')}</option>
          <option value="90">90 {t('account.apikeys.days')}</option>
          <option value="365">365 {t('account.apikeys.days')}</option>
          <option value="never">{t('account.apikeys.never')}</option>
        </select>
        <button
          className="acct-btn acct-btn-primary"
          onClick={create}
          disabled={busy || !name.trim()}
        >
          <Plus size={14} /> {t('account.apikeys.create')}
        </button>
      </div>

      {active.length === 0 ? (
        <p className="acct-empty">{t('account.apikeys.none')}</p>
      ) : (
        <ul className="acct-list">
          {active.map((k) => (
            <li key={k.id} className="acct-list-row">
              <div>
                <strong>
                  {k.name} <code className="acct-key-prefix">bsk_{k.prefix}…</code>
                </strong>
                <span className="acct-meta">
                  {k.expires_at
                    ? t('account.apikeys.expires', {
                        date: new Date(k.expires_at).toLocaleDateString(),
                      })
                    : t('account.apikeys.noExpiry')}
                  {k.last_used_at &&
                    ` · ${t('account.apikeys.lastUsed', { date: new Date(k.last_used_at).toLocaleDateString() })}`}
                </span>
              </div>
              <button
                className="acct-icon-btn"
                onClick={() => revoke(k.id)}
                aria-label={t('account.apikeys.revoke')}
              >
                <Trash2 size={15} />
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
