/**
 * Access Control tab — the central per-plugin-tab permission matrix.
 *
 * Each row is a discovered plugin tab. Admins flip a tab to "restricted" and
 * then grant access to specific roles (a matrix cell grants the
 * tab:<plugin>:<tab_id> permission to that role). Wildcard roles (admin)
 * always have access.
 */

import { useMemo } from 'react';
import { Lock, Unlock, RefreshCw, Check } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useRbac } from '../../hooks/useRbac';
import type { RbacRole } from '../../types';

const tabSlug = (plugin: string, tabId: string) => `tab:${plugin}:${tabId}`;

const AccessTab = () => {
  const { t } = useTranslation();
  const { roles, tabs, loading, error, refreshTabs, toggleRestricted, togglePermission } =
    useRbac();

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
      `}</style>
    </div>
  );
};

export default AccessTab;
