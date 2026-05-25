/**
 * Edit User Modal
 */

import { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import type { User, UpdateUserRequest, PluginTab } from '../../types';
import { ROLES } from '../../types';
import { getPluginTabs } from '../../api/auth';
import { useAuth } from '../../hooks/useAuthContext';

interface EditUserModalProps {
  user: User;
  onClose: () => void;
  onUpdate: (userId: string, data: UpdateUserRequest) => Promise<void>;
  isLoading: boolean;
}

const EditUserModal = ({ user, onClose, onUpdate, isLoading }: EditUserModalProps) => {
  const { accessToken } = useAuth();
  const [email, setEmail] = useState(user.email);
  const [username, setUsername] = useState(user.username || '');
  const [roles, setRoles] = useState<string[]>(user.roles);
  const [isActive, setIsActive] = useState(user.is_active);
  const [allowedTabs, setAllowedTabs] = useState<string[]>(user.allowed_tabs || []);
  const [availableTabs, setAvailableTabs] = useState<PluginTab[]>([]);
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!email) {
      setError('Email is required');
      return;
    }

    if (roles.length === 0) {
      setError('At least one role is required');
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
      setError(err instanceof Error ? err.message : 'Failed to update user');
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
          <h3>Edit User</h3>
          <button onClick={onClose} className="admin-close-btn" disabled={isLoading}>
            <X size={20} />
          </button>
        </div>

        {error && <div className="admin-error-message">{error}</div>}

        <form onSubmit={handleSubmit} className="admin-form">
          <div className="admin-modal-body">
            <div className="admin-form-group">
              <label className="admin-label">Email Address</label>
              <input
                type="email"
                className="admin-input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>

            <div className="admin-form-group">
              <label className="admin-label">Username</label>
              <input
                type="text"
                className="admin-input"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>

            <div className="admin-form-group">
              <label className="admin-label">Roles</label>
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

            {isGuestRole && (
              <div className="admin-form-group">
                <label className="admin-label">Allowed Tabs (Guest Permissions)</label>
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
                      No plugin tabs available
                    </div>
                  )}
                </div>
                <p className="admin-form-hint">
                  Select which tabs the guest user can access. If none selected, all tabs are
                  accessible (read-only).
                </p>
              </div>
            )}

            <div className="admin-form-group">
              <label className="admin-checkbox-label">
                <input
                  type="checkbox"
                  checked={isActive}
                  onChange={(e) => setIsActive(e.target.checked)}
                />
                Account active
              </label>
              {!isActive && (
                <p className="admin-form-hint" style={{ color: 'var(--admin-warning)' }}>
                  Deactivating will revoke all active sessions.
                </p>
              )}
            </div>

            <div className="admin-form-group">
              <label className="admin-label">User Info</label>
              <div style={{ fontSize: '0.8125rem', color: 'var(--admin-text-muted)' }}>
                <p>ID: {user.id}</p>
                <p>MFA: {user.mfa_enabled ? 'Enabled' : 'Disabled'}</p>
                <p>
                  Created:{' '}
                  {user.created_at ? new Date(user.created_at).toLocaleDateString() : 'Unknown'}
                </p>
                <p>
                  Last Login:{' '}
                  {user.last_login ? new Date(user.last_login).toLocaleDateString() : 'Never'}
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
              Cancel
            </button>
            <button type="submit" className="admin-btn admin-btn-primary" disabled={isLoading}>
              {isLoading ? <span className="admin-spinner" /> : 'Save Changes'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default EditUserModal;
