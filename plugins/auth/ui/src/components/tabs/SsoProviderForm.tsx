/** Create/edit form for an SSO identity provider (OIDC or SAML). */

import { useState, type FormEvent } from 'react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../hooks/useAuthContext';
import { upsertProvider, type SsoProvider } from '../../api/sso';

interface Props {
  initial?: SsoProvider | null;
  onSaved: () => void;
  onCancel: () => void;
}

const field = (cfg: Record<string, unknown>, k: string) => (cfg[k] as string) || '';

export default function SsoProviderForm({ initial, onSaved, onCancel }: Props) {
  const { t } = useTranslation();
  const { accessToken } = useAuth();
  const editing = !!initial;
  const [slug, setSlug] = useState(initial?.slug || '');
  const [name, setName] = useState(initial?.name || '');
  const [protocol, setProtocol] = useState<'oidc' | 'saml'>(initial?.protocol || 'oidc');
  const [enabled, setEnabled] = useState(initial?.enabled ?? true);
  const [autoProvision, setAutoProvision] = useState(initial?.auto_provision ?? true);
  const [roles, setRoles] = useState((initial?.default_roles || ['user']).join(', '));
  const [secret, setSecret] = useState('');
  const [cfg, setCfg] = useState<Record<string, string>>(
    (initial?.config as Record<string, string>) || {}
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const set = (k: string, v: string) => setCfg((c) => ({ ...c, [k]: v }));

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!accessToken) return;
    setBusy(true);
    setError('');
    try {
      await upsertProvider(accessToken, slug, {
        name,
        protocol,
        enabled,
        auto_provision: autoProvision,
        config: cfg,
        secret: secret || null,
        default_roles: roles
          .split(',')
          .map((r) => r.trim())
          .filter(Boolean),
      });
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : t('sso.error'));
    } finally {
      setBusy(false);
    }
  };

  const input = (label: string, value: string, on: (v: string) => void, ph = '') => (
    <label className="acct-label">
      {label}
      <input
        className="acct-input"
        value={value}
        onChange={(e) => on(e.target.value)}
        placeholder={ph}
      />
    </label>
  );

  return (
    <form onSubmit={submit} className="sso-form">
      {error && <div className="acct-alert acct-alert-error">{error}</div>}
      <div className="sso-form-grid">
        {input(t('sso.fields.slug'), slug, setSlug, 'okta')}
        {input(t('sso.fields.name'), name, setName, 'Okta')}
        <label className="acct-label">
          {t('sso.fields.protocol')}
          <select
            className="acct-input"
            value={protocol}
            disabled={editing}
            onChange={(e) => setProtocol(e.target.value as 'oidc' | 'saml')}
          >
            <option value="oidc">OIDC</option>
            <option value="saml">SAML 2.0</option>
          </select>
        </label>
        {input(t('sso.fields.defaultRoles'), roles, setRoles, 'user')}
      </div>

      {protocol === 'oidc' ? (
        <div className="sso-form-grid">
          {input(t('sso.fields.clientId'), field(cfg, 'client_id'), (v) => set('client_id', v))}
          {input(
            t('sso.fields.clientSecret'),
            secret,
            setSecret,
            initial?.has_secret ? '••••••• (unchanged)' : ''
          )}
          {input(
            t('sso.fields.issuer'),
            field(cfg, 'issuer'),
            (v) => set('issuer', v),
            'https://idp.example.com'
          )}
          {input(
            t('sso.fields.scopes'),
            field(cfg, 'scopes'),
            (v) => set('scopes', v),
            'openid email profile'
          )}
        </div>
      ) : (
        <div className="sso-form-grid">
          {input(t('sso.fields.idpEntityId'), field(cfg, 'idp_entity_id'), (v) =>
            set('idp_entity_id', v)
          )}
          {input(t('sso.fields.idpSsoUrl'), field(cfg, 'idp_sso_url'), (v) =>
            set('idp_sso_url', v)
          )}
          <label className="acct-label sso-span2">
            {t('sso.fields.idpCert')}
            <textarea
              className="acct-input sso-textarea"
              value={field(cfg, 'idp_x509cert')}
              onChange={(e) => set('idp_x509cert', e.target.value)}
              rows={3}
            />
          </label>
        </div>
      )}

      <div className="sso-toggles">
        <label className="sso-check">
          <input type="checkbox" checked={enabled} onChange={(e) => setEnabled(e.target.checked)} />{' '}
          {t('sso.fields.enabled')}
        </label>
        <label className="sso-check">
          <input
            type="checkbox"
            checked={autoProvision}
            onChange={(e) => setAutoProvision(e.target.checked)}
          />{' '}
          {t('sso.fields.autoProvision')}
        </label>
      </div>

      <div className="sso-form-actions">
        <button type="button" className="acct-btn acct-btn-ghost" onClick={onCancel}>
          {t('sso.cancel')}
        </button>
        <button
          type="submit"
          className="acct-btn acct-btn-primary"
          disabled={busy || !slug || !name}
        >
          {busy ? t('sso.saving') : t('sso.save')}
        </button>
      </div>
    </form>
  );
}
