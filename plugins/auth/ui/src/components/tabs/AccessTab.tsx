/**
 * Access Control tab — the central per-plugin-tab permission matrix.
 *
 * Each row is a discovered plugin tab. Admins flip a tab to "restricted" and
 * then grant access to specific roles (a matrix cell grants the
 * tab:<plugin>:<tab_id> permission to that role). Wildcard roles (admin)
 * always have access.
 */

import { useEffect, useMemo, useState } from 'react';
import { Lock, Unlock, RefreshCw, Check, ShieldCheck } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useRbac } from '../../hooks/useRbac';
import { getMfaPolicy, setMfaPolicy } from '../../api/security';
import type { RbacRole } from '../../types';

const tabSlug = (plugin: string, tabId: string) => `tab:${plugin}:${tabId}`;

const AccessTab = () => {
  const { t } = useTranslation();
  const { roles, tabs, loading, error, refreshTabs, toggleRestricted, togglePermission } =
    useRbac();

  const [mfaAll, setMfaAll] = useState(false);
  const [mfaSaving, setMfaSaving] = useState(false);

  useEffect(() => {
    getMfaPolicy()
      .then((p) => setMfaAll(p.mfa_required_all))
      .catch(() => {});
  }, []);

  const toggleMfaAll = async () => {
    const next = !mfaAll;
    setMfaSaving(true);
    setMfaAll(next); // optimistic
    try {
      await setMfaPolicy(next);
    } catch {
      setMfaAll(!next); // revert on failure
    } finally {
      setMfaSaving(false);
    }
  };

  // Roles that can be granted per-tab access (wildcard roles always have it).
  const grantableRoles = useMemo(() => roles.filter((r) => !r.permissions.includes('*')), [roles]);
  const wildcardRoles = useMemo(() => roles.filter((r) => r.permissions.includes('*')), [roles]);

  const roleHasTab = (role: RbacRole, slug: string) => role.permissions.includes(slug);

  return (
    <div className="access-tab">
      <div className="access-header">
        <div className="access-title">
          <Lock size={20} />
          <h2>{t('access.title')}</h2>
        </div>
        <button className="admin-btn admin-btn-ghost" onClick={() => refreshTabs()}>
          <RefreshCw size={16} /> {t('access.refreshTabs')}
        </button>
      </div>
      <p className="access-desc">{t('access.description')}</p>
      {wildcardRoles.length > 0 && <p className="access-note">{t('access.adminAlways')}</p>}

      {error && <div className="admin-alert admin-alert-error">{error}</div>}

      <div className="admin-card mfa-policy-card">
        <div className="mfa-policy-row">
          <div className="mfa-policy-info">
            <ShieldCheck size={18} />
            <div>
              <div className="mfa-policy-title">{t('access.security.mfaAll')}</div>
              <div className="mfa-policy-hint">{t('access.security.mfaAllHint')}</div>
            </div>
          </div>
          <button
            type="button"
            role="switch"
            aria-checked={mfaAll}
            disabled={mfaSaving}
            className={`mfa-switch ${mfaAll ? 'on' : ''}`}
            onClick={toggleMfaAll}
          >
            <span className="mfa-switch-knob" />
          </button>
        </div>
      </div>

      <div className="admin-card">
        {loading ? (
          <div className="admin-empty">
            <div className="admin-spinner admin-spinner-lg" />
            <p className="admin-empty-text">{t('common.loading')}</p>
          </div>
        ) : tabs.length === 0 ? (
          <div className="admin-empty">
            <p className="admin-empty-title">{t('access.empty')}</p>
          </div>
        ) : (
          <table className="admin-table access-table">
            <thead>
              <tr>
                <th>{t('access.columns.tab')}</th>
                <th>{t('access.columns.plugin')}</th>
                <th>{t('access.columns.policy')}</th>
                {grantableRoles.map((r) => (
                  <th key={r.id} className="role-col">
                    {r.name}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {tabs.map((tab) => {
                const slug = tabSlug(tab.plugin, tab.tab_id);
                return (
                  <tr key={slug}>
                    <td>{tab.label}</td>
                    <td>
                      <code className="plugin-name">{tab.plugin}</code>
                    </td>
                    <td>
                      <button
                        type="button"
                        className={`policy-toggle ${tab.restricted ? 'restricted' : 'open'}`}
                        onClick={() => toggleRestricted(tab.plugin, tab.tab_id, !tab.restricted)}
                        title={tab.restricted ? t('access.restrictedHint') : t('access.openHint')}
                      >
                        {tab.restricted ? <Lock size={13} /> : <Unlock size={13} />}
                        {tab.restricted ? t('access.restricted') : t('access.open')}
                      </button>
                    </td>
                    {grantableRoles.map((role) => {
                      const granted = roleHasTab(role, slug);
                      const disabled = !tab.restricted;
                      return (
                        <td key={role.id} className="role-col">
                          <button
                            type="button"
                            disabled={disabled}
                            className={`perm-check ${granted ? 'on' : ''} ${disabled ? 'muted' : ''}`}
                            onClick={() => togglePermission(role, slug, !granted)}
                          >
                            {granted && <Check size={12} />}
                          </button>
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        )}
      </div>

      <style>{`
        .access-tab { display: flex; flex-direction: column; gap: 0.75rem; }
        .access-header { display: flex; align-items: center; justify-content: space-between; }
        .access-title { display: flex; align-items: center; gap: 0.75rem; color: var(--admin-text); }
        .access-title h2 { margin: 0; }
        .access-desc { margin: 0; color: var(--admin-text-muted); font-size: 0.875rem; }
        .access-note { margin: 0; color: var(--admin-text-muted); font-size: 0.8rem; font-style: italic; }
        .access-table th.role-col, .access-table td.role-col { text-align: center; }
        .plugin-name { font-family: monospace; font-size: 0.8rem; color: var(--admin-text-muted); }
        .policy-toggle { display: inline-flex; align-items: center; gap: 0.35rem; padding: 0.25rem 0.6rem;
          border-radius: 9999px; font-size: 0.75rem; cursor: pointer; border: 1px solid transparent; }
        .policy-toggle.open { background: hsla(140,60%,45%,0.15); color: var(--admin-success, #4ade80); }
        .policy-toggle.restricted { background: hsla(30,90%,55%,0.15); color: #f59e0b; }
        .perm-check { width: 20px; height: 20px; border-radius: 0.35rem;
          border: 1px solid var(--admin-border, hsla(220,25%,40%,0.4)); background: transparent;
          display: inline-flex; align-items: center; justify-content: center; cursor: pointer; color: #fff; }
        .perm-check.on { background: var(--admin-accent); border-color: var(--admin-accent); }
        .perm-check.muted { opacity: 0.3; cursor: not-allowed; }
        .mfa-policy-card { padding: 0.9rem 1rem; }
        .mfa-policy-row { display: flex; align-items: center; justify-content: space-between; gap: 1rem; }
        .mfa-policy-info { display: flex; align-items: center; gap: 0.7rem; color: var(--admin-text); }
        .mfa-policy-title { font-weight: 600; font-size: 0.9rem; }
        .mfa-policy-hint { color: var(--admin-text-muted); font-size: 0.8rem; }
        .mfa-switch { position: relative; width: 44px; height: 24px; border-radius: 9999px; flex-shrink: 0;
          border: none; cursor: pointer; background: var(--admin-border, hsla(220,25%,40%,0.4)); transition: background 0.2s; }
        .mfa-switch.on { background: var(--admin-accent); }
        .mfa-switch:disabled { opacity: 0.6; cursor: wait; }
        .mfa-switch-knob { position: absolute; top: 3px; left: 3px; width: 18px; height: 18px; border-radius: 50%;
          background: #fff; transition: transform 0.2s; }
        .mfa-switch.on .mfa-switch-knob { transform: translateX(20px); }
      `}</style>
    </div>
  );
};

export default AccessTab;
