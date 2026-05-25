/**
 * Create User Modal
 */

import { useState, useEffect } from 'react';
import { X } from 'lucide-react';
import type { CreateUserRequest, PluginTab } from '../../types';
import { ROLES } from '../../types';
import { getPluginTabs } from '../../api/auth';
import { useAuth } from '../../hooks/useAuthContext';

interface CreateUserModalProps {
  onClose: () => void;
  onCreate: (data: CreateUserRequest) => Promise<void>;
  isLoading: boolean;
}

const CreateUserModal = ({ onClose, onCreate, isLoading }: CreateUserModalProps) => {
  const { accessToken } = useAuth();
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [generatePassword, setGeneratePassword] = useState(true);
  const [roles, setRoles] = useState<string[]>(['user']);
  const [allowedTabs, setAllowedTabs] = useState<string[]>([]);
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

    if (!generatePassword && !password) {
      setError('Password is required');
      return;
    }

    if (roles.length === 0) {
      setError('At least one role is required');
      return;
    }

    try {
      await onCreate({
        email,
        username: username.trim() || undefined,
        password: generatePassword ? undefined : password,
        roles,
        allowed_tabs: isGuestRole && allowedTabs.length > 0 ? allowedTabs : undefined,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create user');
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
          <h3>Create New User</h3>
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
                placeholder="user@example.com"
                required
              />
            </div>

            <div className="admin-form-group">
              <label className="admin-label">Username (Optional)</label>
              <input
                type="text"
                className="admin-input"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="jdoe"
              />
            </div>

            <div className="admin-form-group">
              <label className="admin-label">Password</label>
              <div className="admin-checkbox-label" style={{ marginBottom: '0.5rem' }}>
                <input
                  type="checkbox"
                  checked={generatePassword}
                  onChange={(e) => setGeneratePassword(e.target.checked)}
                />
                Auto-generate secure password
              </div>
              {!generatePassword && (
                <input
                  type="password"
                  className="admin-input"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter password"
                  required={!generatePassword}
                />
              )}
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
              {isLoading ? <span className="admin-spinner" /> : 'Create User'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CreateUserModal;
