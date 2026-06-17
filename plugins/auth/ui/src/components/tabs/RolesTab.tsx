/**
 * Roles & Permissions tab.
 *
 * Lists roles (system + custom), lets admins create/delete custom roles and
 * toggle individual permissions per role. Tab permissions (tab:*) are managed
 * from the Access Control tab and hidden here to keep this view focused.
 */

import { useMemo, useState } from 'react';
import { Shield, Plus, Trash2, Check } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useRbac } from '../../hooks/useRbac';
import type { RbacRole } from '../../types';
import * as rbac from '../../api/rbac';

const RolesTab = () => {
  const { t } = useTranslation();
  const { roles, permissions, loading, error, reload, togglePermission } = useRbac();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ slug: '', name: '', description: '' });

  const nonTabPerms = useMemo(
    () => permissions.filter((p) => !p.slug.startsWith('tab:')),
    [permissions]
  );
  const grouped = useMemo(() => {
    const map: Record<string, typeof nonTabPerms> = {};
    for (const p of nonTabPerms) (map[p.category] ||= []).push(p);
    return map;
  }, [nonTabPerms]);

  const selected = roles.find((r) => r.id === selectedId) || roles[0] || null;
  const isWildcard = selected?.permissions.includes('*');

  const handleCreate = async () => {
    if (!form.slug || !form.name) return;
    await rbac.createRole(form);
    setForm({ slug: '', name: '', description: '' });
    setCreating(false);
    await reload();
  };

  const handleDelete = async (role: RbacRole) => {
    if (!window.confirm(t('roles.deleteConfirm', { name: role.name }))) return;
    await rbac.deleteRole(role.id);
    if (selectedId === role.id) setSelectedId(null);
    await reload();
  };

  return (
    <div className="roles-tab">
      <div className="roles-header">
        <div className="roles-title">
          <Shield size={20} />
          <h2>{t('roles.title')}</h2>
        </div>
        <button className="admin-btn admin-btn-primary" onClick={() => setCreating(true)}>
          <Plus size={16} /> {t('roles.addRole')}
        </button>
      </div>

      {error && <div className="admin-alert admin-alert-error">{error}</div>}

      {creating && (
        <div className="admin-card role-create">
          <input
            className="admin-input"
            placeholder={t('roles.slug')}
            value={form.slug}
            onChange={(e) => setForm({ ...form, slug: e.target.value })}
          />
          <input
            className="admin-input"
            placeholder={t('roles.name')}
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <input
            className="admin-input"
            placeholder={t('roles.description')}
            value={form.description}
            onChange={(e) => setForm({ ...form, description: e.target.value })}
          />
          <button className="admin-btn admin-btn-primary" onClick={handleCreate}>
            {t('common.create')}
          </button>
          <button className="admin-btn admin-btn-ghost" onClick={() => setCreating(false)}>
            {t('common.cancel')}
          </button>
        </div>
      )}

      {loading ? (
        <div className="admin-empty">
          <div className="admin-spinner admin-spinner-lg" />
          <p className="admin-empty-text">{t('common.loading')}</p>
        </div>
      ) : (
        <div className="roles-grid">
          <div className="roles-list">
            {roles.map((role) => (
              <button
                key={role.id}
                className={`role-item ${selected?.id === role.id ? 'active' : ''}`}
                onClick={() => setSelectedId(role.id)}
              >
                <div className="role-item-main">
                  <span className="role-item-name">{role.name}</span>
                  <span className={`role-badge ${role.is_system ? 'sys' : 'custom'}`}>
                    {role.is_system ? t('roles.system') : t('roles.custom')}
                  </span>
                </div>
                <span className="role-item-meta">
                  {role.permissions.includes('*')
                    ? t('roles.wildcardNote')
                    : t('roles.permissionsCount', { count: role.permissions.length })}
                </span>
              </button>
            ))}
            {roles.length === 0 && <p className="admin-empty-text">{t('roles.empty')}</p>}
          </div>

          {selected && (
            <div className="admin-card role-detail">
              <div className="role-detail-head">
                <div>
                  <h3>{selected.name}</h3>
                  <code className="role-slug">{selected.slug}</code>
                </div>
                {!selected.is_system && (
                  <button
                    className="admin-btn admin-btn-ghost admin-btn-icon"
                    onClick={() => handleDelete(selected)}
                    title={t('common.delete')}
                  >
                    <Trash2 size={16} />
                  </button>
                )}
              </div>

              {isWildcard ? (
                <p className="role-wildcard">{t('roles.wildcardNote')}</p>
              ) : (
                <div className="perm-groups">
                  {Object.entries(grouped).map(([category, perms]) => (
                    <div key={category} className="perm-group">
                      <h4>{t(`roles.permissionCategories.${category}`, category)}</h4>
                      {perms.map((p) => {
                        const granted = selected.permissions.includes(p.slug);
                        return (
                          <label key={p.slug} className="perm-row">
                            <button
                              type="button"
                              className={`perm-check ${granted ? 'on' : ''}`}
                              onClick={() => togglePermission(selected, p.slug, !granted)}
                            >
                              {granted && <Check size={12} />}
                            </button>
                            <span className="perm-slug">{p.slug}</span>
                            <span className="perm-desc">{p.description}</span>
                          </label>
                        );
                      })}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      <style>{`
        .roles-tab { display: flex; flex-direction: column; gap: 1.25rem; }
        .roles-header { display: flex; align-items: center; justify-content: space-between; }
        .roles-title { display: flex; align-items: center; gap: 0.75rem; color: var(--admin-text); }
        .roles-title h2 { margin: 0; }
        .role-create { display: flex; gap: 0.5rem; flex-wrap: wrap; padding: 1rem; }
        .roles-grid { display: grid; grid-template-columns: 280px 1fr; gap: 1rem; align-items: start; }
        .roles-list { display: flex; flex-direction: column; gap: 0.5rem; }
        .role-item { text-align: left; padding: 0.75rem; border-radius: 0.5rem;
          background: var(--admin-surface, hsla(220,25%,15%,0.5)); border: 1px solid transparent;
          cursor: pointer; display: flex; flex-direction: column; gap: 0.25rem; color: var(--admin-text); }
        .role-item.active { border-color: var(--admin-accent); }
        .role-item-main { display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; }
        .role-item-name { font-weight: 600; }
        .role-item-meta { font-size: 0.75rem; color: var(--admin-text-muted); }
        .role-badge { font-size: 0.65rem; padding: 0.1rem 0.4rem; border-radius: 9999px; text-transform: uppercase; }
        .role-badge.sys { background: hsla(265,80%,60%,0.18); color: #b59bff; }
        .role-badge.custom { background: hsla(200,80%,50%,0.18); color: var(--admin-accent); }
        .role-detail { padding: 1.25rem; }
        .role-detail-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem; }
        .role-detail-head h3 { margin: 0 0 0.25rem; }
        .role-slug { font-size: 0.75rem; color: var(--admin-text-muted); }
        .role-wildcard { color: var(--admin-success); font-weight: 500; }
        .perm-groups { display: flex; flex-direction: column; gap: 1rem; }
        .perm-group h4 { margin: 0 0 0.5rem; font-size: 0.8rem; text-transform: uppercase; color: var(--admin-text-muted); }
        .perm-row { display: grid; grid-template-columns: 24px 180px 1fr; align-items: center; gap: 0.5rem;
          padding: 0.25rem 0; cursor: pointer; }
        .perm-check { width: 20px; height: 20px; border-radius: 0.35rem; border: 1px solid var(--admin-border, hsla(220,25%,40%,0.4));
          background: transparent; display: flex; align-items: center; justify-content: center; cursor: pointer; color: #fff; }
        .perm-check.on { background: var(--admin-accent); border-color: var(--admin-accent); }
        .perm-slug { font-family: monospace; font-size: 0.8rem; color: var(--admin-text); }
        .perm-desc { font-size: 0.8rem; color: var(--admin-text-muted); }
        @media (max-width: 820px) { .roles-grid { grid-template-columns: 1fr; } }
      `}</style>
    </div>
  );
};

export default RolesTab;
