/**
 * Roles & Permissions tab.
 *
 * Lists roles (system + custom), lets admins create custom roles — optionally
 * from a predefined template — delete them, and edit each role's permissions
 * via a grouped matrix with bulk toggles and a batched, diff-aware save. Tab
 * permissions (``tab:*``) are managed from the Access Control tab and hidden
 * here; the editor preserves them on save.
 */

import { useMemo, useState } from 'react';
import { Plus, Shield, Trash2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useRbac } from '../../../hooks/useRbac';
import type { RbacPermission, RbacRole } from '../../../types';
import * as rbac from '../../../api/rbac';
import CreateRoleForm, { type NewRole } from './parts/CreateRoleForm';
import PermissionMatrix from './parts/PermissionMatrix';
import RoleList from './parts/RoleList';
import { useRoleEditor, useRoleTemplates } from './hooks';
import { ROLES_STYLES } from './styles';
import type { RoleTemplate } from '../../../types';

const RolesTab = () => {
  const { t } = useTranslation();
  const { roles, permissions, loading, error, reload } = useRbac();
  const templates = useRoleTemplates();
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);

  const selected = roles.find((r) => r.id === selectedId) || roles[0] || null;
  const isWildcard = selected?.permissions.includes('*') ?? false;
  const editor = useRoleEditor(isWildcard ? null : selected, reload);

  const permsByCategory = useMemo(() => {
    const map: Record<string, RbacPermission[]> = {};
    for (const p of permissions) {
      if (p.slug.startsWith('tab:') || p.slug === '*') continue;
      (map[p.category] ||= []).push(p);
    }
    return map;
  }, [permissions]);

  const handleCreate = async (form: NewRole, template: RoleTemplate | null) => {
    const role = await rbac.createRole(form);
    if (template && template.permissions.length > 0) {
      await rbac.setRolePermissions(role.id, template.permissions);
    }
    setCreating(false);
    await reload();
    setSelectedId(role.id);
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
        <CreateRoleForm
          templates={templates}
          onCreate={handleCreate}
          onCancel={() => setCreating(false)}
        />
      )}

      {loading ? (
        <div className="admin-empty">
          <div className="admin-spinner admin-spinner-lg" />
          <p className="admin-empty-text">{t('common.loading')}</p>
        </div>
      ) : (
        <div className="roles-grid">
          <RoleList roles={roles} selectedId={selected?.id ?? null} onSelect={setSelectedId} />

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
                <PermissionMatrix
                  role={selected}
                  permsByCategory={permsByCategory}
                  editor={editor}
                />
              )}
            </div>
          )}
        </div>
      )}

      <style>{ROLES_STYLES}</style>
    </div>
  );
};

export default RolesTab;
