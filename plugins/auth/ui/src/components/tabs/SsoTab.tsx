/** Admin tab: configure SSO identity providers (OIDC / SAML). */

import { useCallback, useEffect, useState } from 'react';
import { Plus, Trash2, Pencil, Globe } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../hooks/useAuthContext';
import { listProviders, deleteProvider, type SsoProvider } from '../../api/sso';
import SsoProviderForm from './SsoProviderForm';
import './sso.css';

export default function SsoTab() {
  const { t } = useTranslation();
  const { accessToken } = useAuth();
  const [providers, setProviders] = useState<SsoProvider[]>([]);
  const [editing, setEditing] = useState<SsoProvider | null>(null);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(() => {
    if (!accessToken) return;
    listProviders(accessToken)
      .then(setProviders)
      .catch((e) => setError(e instanceof Error ? e.message : 'Error'));
  }, [accessToken]);

  useEffect(load, [load]);

  const remove = async (slug: string) => {
    if (!accessToken || !window.confirm(t('sso.confirmDelete'))) return;
    try {
      await deleteProvider(accessToken, slug);
      load();
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error');
    }
  };

  const showForm = creating || editing;

  return (
    <div className="sso-tab">
      <div className="sso-head">
        <div>
          <h2 className="sso-title">
            <Globe size={18} /> {t('sso.title')}
          </h2>
          <p className="sso-desc">{t('sso.desc')}</p>
        </div>
        {!showForm && (
          <button className="acct-btn acct-btn-primary" onClick={() => setCreating(true)}>
            <Plus size={14} /> {t('sso.add')}
          </button>
        )}
      </div>

      {error && <div className="acct-alert acct-alert-error">{error}</div>}

      {showForm ? (
        <div className="sso-card">
          <h3 className="sso-card-title">{editing ? t('sso.editTitle') : t('sso.addTitle')}</h3>
          <SsoProviderForm
            initial={editing}
            onSaved={() => {
              setEditing(null);
              setCreating(false);
              load();
            }}
            onCancel={() => {
              setEditing(null);
              setCreating(false);
            }}
          />
        </div>
      ) : providers.length === 0 ? (
        <div className="sso-empty">{t('sso.none')}</div>
      ) : (
        <ul className="sso-list">
          {providers.map((p) => (
            <li key={p.id} className="sso-row">
              <div className="sso-row-main">
                <span className={`sso-proto sso-proto-${p.protocol}`}>
                  {p.protocol.toUpperCase()}
                </span>
                <div>
                  <strong>{p.name}</strong>
                  <span className="sso-slug">/{p.slug}</span>
                </div>
                {!p.enabled && <span className="sso-disabled">{t('sso.disabled')}</span>}
              </div>
              <div className="sso-row-actions">
                <button
                  className="acct-icon-btn sso-edit"
                  onClick={() => setEditing(p)}
                  aria-label={t('sso.edit')}
                >
                  <Pencil size={15} />
                </button>
                <button
                  className="acct-icon-btn"
                  onClick={() => remove(p.slug)}
                  aria-label={t('sso.delete')}
                >
                  <Trash2 size={15} />
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
