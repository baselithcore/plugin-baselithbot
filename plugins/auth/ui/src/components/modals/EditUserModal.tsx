/**
 * Edit User Modal
 */

import { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { User, UpdateUserRequest, PluginTab, RbacRole } from '../../types';
import { ROLES } from '../../types';
import { getPluginTabs } from '../../api/auth';
import * as rbac from '../../api/rbac';
import { useAuth } from '../../hooks/useAuthContext';

interface EditUserModalProps {
  user: User;
  onClose: () => void;
  onUpdate: (userId: string, data: UpdateUserRequest) => Promise<void>;
  isLoading: boolean;
}

const EditUserModal = ({ user, onClose, onUpdate, isLoading }: EditUserModalProps) => {
  const { t, i18n } = useTranslation();
  const { accessToken } = useAuth();
  const [email, setEmail] = useState(user.email);
  const [username, setUsername] = useState(user.username || '');
  const [roles, setRoles] = useState<string[]>(user.roles);
  const [isActive, setIsActive] = useState(user.is_active);
  const [mfaRequired, setMfaRequired] = useState(!!user.mfa_required);
  const [allowedTabs, setAllowedTabs] = useState<string[]>(user.allowed_tabs || []);
  const [availableTabs, setAvailableTabs] = useState<PluginTab[]>([]);
  const [customRoles, setCustomRoles] = useState<RbacRole[]>([]);
  const [assignedRoleIds, setAssignedRoleIds] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);

  const isGuestRole = roles.includes('guest');

  useEffect(() => {
    const fetchTabs = async () => {
      if (accessToken) {
        try {
          const tabs = await getPluginTabs(accessToken);
          setAvailableTabs(tabs);
        } catch (err) {
          console.error('Failed to load plugin tabs', err);
        }
      }
    };
    fetchTabs();
  }, [accessToken]);

  useEffect(() => {
    const fetchRoles = async () => {
      try {
        const [all, assigned] = await Promise.all([rbac.listRoles(), rbac.getUserRoles(user.id)]);
        setCustomRoles(all.filter((r) => !r.is_system));
        setAssignedRoleIds(assigned.map((r) => r.id));
      } catch (err) {
        console.error('Failed to load custom roles', err);
      }
    };
    fetchRoles();
  }, [user.id]);

  const toggleCustomRole = async (role: RbacRole) => {
    const has = assignedRoleIds.includes(role.id);
    try {
      if (has) {
        await rbac.revokeUserRole(user.id, role.id);
        setAssignedRoleIds((prev) => prev.filter((id) => id !== role.id));
      } else {
        await rbac.assignUserRole(user.id, role.id);
        setAssignedRoleIds((prev) => [...prev, role.id]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('errors.saveFailed'));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!email) {
      setError(t('modals.errors.emailRequired'));
      return;
    }

    if (roles.length === 0) {
      setError(t('modals.errors.roleRequired'));
      return;
    }

    const updates: UpdateUserRequest = {};

    if (email !== user.email) {
      updates.email = email;
    }

    const trimmedUsername = username.trim() || null;
    if (trimmedUsername !== user.username) {
      updates.username = trimmedUsername;
    }

    if (JSON.stringify(roles.sort()) !== JSON.stringify(user.roles.sort())) {
      updates.roles = roles;
    }

    if (mfaRequired !== !!user.mfa_required) {
      updates.mfa_required = mfaRequired;
    }
    if (isActive !== user.is_active) {
      updates.is_active = isActive;
    }

    // Handle allowed_tabs for guest role
    const currentTabs = user.allowed_tabs || [];
    const tabsChanged = JSON.stringify(allowedTabs.sort()) !== JSON.stringify(currentTabs.sort());
    if (isGuestRole && tabsChanged) {
      updates.allowed_tabs = allowedTabs.length > 0 ? allowedTabs : null;
    } else if (!isGuestRole && currentTabs.length > 0) {
      // Clear allowed_tabs if role changed from guest
      updates.allowed_tabs = null;
    }

    try {
      if (Object.keys(updates).length > 0) {
        await onUpdate(user.id, updates);
      } else {
        onClose();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('modals.errors.updateFailed'));
    }
  };

  const toggleRole = (role: string) => {
    if (roles.includes(role)) {
      setRoles(roles.filter((r) => r !== role));
    } else {
      setRoles([...roles, role]);
    }
  };

  const toggleTab = (tabId: string) => {
    if (allowedTabs.includes(tabId)) {
      setAllowedTabs(allowedTabs.filter((t) => t !== tabId));
    } else {
      setAllowedTabs([...allowedTabs, tabId]);
    }
  };

  return (
    <div className="admin-modal-overlay">
      <div className="admin-modal">
        <div className="admin-modal-header">
          <h3>{t('modals.editUser.title')}</h3>
          <button onClick={onClose} className="admin-close-btn" disabled={isLoading}>
            <X size={20} />
          </button>
        </div>

        {error && <div className="admin-error-message">{error}</div>}

        <form onSubmit={handleSubmit} className="admin-form">
          <div className="admin-modal-body">
            <div className="admin-form-group">
              <label className="admin-label">{t('modals.fields.emailAddress')}</label>
              <input
                type="email"
                className="admin-input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div className="admin-form-group">
              <label className="admin-label">{t('modals.fields.username')}</label>
              <input
                type="text"
                className="admin-input"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>

            <div className="admin-form-group">
              <label className="admin-label">{t('modals.fields.roles')}</label>
              <div className="admin-checkbox-group">
                {ROLES.map((role) => (
                  <label key={role} className="admin-checkbox-label">
                    <input
                      type="checkbox"
                      checked={roles.includes(role)}
                      onChange={() => toggleRole(role)}
                    />
                    {role.charAt(0).toUpperCase() + role.slice(1)}
                  </label>
                ))}
              </div>
            </div>

            {customRoles.length > 0 && (
              <div className="admin-form-group">
                <label className="admin-label">{t('modals.editUser.assignRoles')}</label>
                <div className="admin-checkbox-group">
                  {customRoles.map((role) => (
                    <label key={role.id} className="admin-checkbox-label">
                      <input
                        type="checkbox"
                        checked={assignedRoleIds.includes(role.id)}
                        onChange={() => toggleCustomRole(role)}
                      />
                      {role.name}{' '}
                      <span style={{ opacity: 0.6, fontSize: '0.8em' }}>({role.slug})</span>
                    </label>
                  ))}
                </div>
                <p className="admin-form-hint">{t('modals.editUser.assignRolesHint')}</p>
              </div>
            )}

            {isGuestRole && (
              <div className="admin-form-group">
                <label className="admin-label">{t('modals.fields.allowedTabs')}</label>
                <div className="admin-checkbox-group">
                  {availableTabs.length > 0 ? (
                    availableTabs.map((tab) => (
                      <label key={tab.id} className="admin-checkbox-label">
                        <input
                          type="checkbox"
                          checked={allowedTabs.includes(tab.id)}
                          onChange={() => toggleTab(tab.id)}
                        />
                        {tab.label}{' '}
                        <span style={{ opacity: 0.6, fontSize: '0.8em' }}>({tab.plugin})</span>
                      </label>
                    ))
                  ) : (
                    <div style={{ color: '#888', fontStyle: 'italic' }}>
                      {t('modals.noPluginTabs')}
                    </div>
                  )}
                </div>
                <p className="admin-form-hint">{t('modals.allowedTabsHint')}</p>
              </div>
            )}

            <div className="admin-form-group">
              <label className="admin-checkbox-label">
                <input
                  type="checkbox"
                  checked={isActive}
                  onChange={(e) => setIsActive(e.target.checked)}
                />
                {t('modals.fields.accountActive')}
              </label>
              {!isActive && (
                <p className="admin-form-hint" style={{ color: 'var(--admin-warning)' }}>
                  {t('modals.deactivateWarning')}
                </p>
              )}
            </div>

            <div className="admin-form-group">
              <label className="admin-checkbox-label">
                <input
                  type="checkbox"
                  checked={mfaRequired}
                  onChange={(e) => setMfaRequired(e.target.checked)}
                />
                {t('modals.fields.mfaRequired')}
              </label>
              <p className="admin-form-hint">{t('modals.fields.mfaRequiredHint')}</p>
            </div>

            <div className="admin-form-group">
              <label className="admin-label">{t('modals.fields.userInfo')}</label>
              <div style={{ fontSize: '0.8125rem', color: 'var(--admin-text-muted)' }}>
                <p>{t('modals.info.id', { id: user.id })}</p>
                <p>
                  {t('modals.info.mfa', {
                    status: user.mfa_enabled ? t('common.enabled') : t('common.disabled'),
                  })}
                </p>
                <p>
                  {t('modals.info.created', {
                    date: user.created_at
                      ? new Date(user.created_at).toLocaleDateString(i18n.language)
                      : t('common.unknown'),
                  })}
                </p>
                <p>
                  {t('modals.info.lastLogin', {
                    date: user.last_login
                      ? new Date(user.last_login).toLocaleDateString(i18n.language)
                      : t('common.never'),
                  })}
                </p>
              </div>
            </div>
          </div>

          <div className="admin-modal-footer">
            <button
              type="button"
              className="admin-btn admin-btn-secondary"
              onClick={onClose}
              disabled={isLoading}
            >
              {t('common.cancel')}
            </button>
            <button type="submit" className="admin-btn admin-btn-primary" disabled={isLoading}>
              {isLoading ? <span className="admin-spinner" /> : t('modals.editUser.submit')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default EditUserModal;
