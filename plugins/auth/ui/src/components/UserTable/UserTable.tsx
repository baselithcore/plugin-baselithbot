/**
 * User Table Component
 *
 * Displays a table of users with actions.
 */

import { Edit, Trash2, Key, Unlock, ShieldOff, LogOut, MoreVertical, Check, X } from 'lucide-react';
import { useState, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import type { User } from '../../types';
import { PortalDropdown } from '../ui/PortalDropdown';

interface UserTableProps {
  users: User[];
  isLoading: boolean;
  onEdit: (user: User) => void;
  onDelete: (user: User) => void;
  onResetPassword: (user: User) => void;
  onUnlock: (user: User) => void;
  onRevokeSessions: (user: User) => void;
  onDisableMFA: (user: User) => void;
}

interface ActionMenuProps {
  user: User;
  onEdit: () => void;
  onDelete: () => void;
  onResetPassword: () => void;
  onUnlock: () => void;
  onRevokeSessions: () => void;
  onDisableMFA: () => void;
}

const ActionMenu = ({
  user,
  onEdit,
  onDelete,
  onResetPassword,
  onUnlock,
  onRevokeSessions,
  onDisableMFA,
}: ActionMenuProps) => {
  const { t } = useTranslation();
  const [isOpen, setIsOpen] = useState(false);
  const buttonRef = useRef<HTMLButtonElement>(null);

  // We don't need the document click listener here anymore because
  // PortalDropdown handles the outside click detection.

  return (
    <div className="user-actions-menu">
      <button
        ref={buttonRef}
        className="admin-btn admin-btn-ghost admin-btn-icon admin-btn-sm"
        onClick={() => setIsOpen(!isOpen)}
      >
        <MoreVertical size={16} />
      </button>

      <PortalDropdown isOpen={isOpen} onClose={() => setIsOpen(false)} triggerRef={buttonRef}>
        {/* We reuse the existing class structure inside the portal */}
        {/* The PortalDropdown wrapper provides the .user-actions-dropdown class */}

        <button
          className="user-action-item"
          onClick={() => {
            onEdit();
            setIsOpen(false);
          }}
        >
          <Edit size={14} />
          <span>{t('users.actions.edit')}</span>
        </button>

        <button
          className="user-action-item"
          onClick={() => {
            onResetPassword();
            setIsOpen(false);
          }}
        >
          <Key size={14} />
          <span>{t('users.actions.resetPassword')}</span>
        </button>

        <button
          className="user-action-item"
          onClick={() => {
            onRevokeSessions();
            setIsOpen(false);
          }}
        >
          <LogOut size={14} />
          <span>{t('users.actions.revokeSessions')}</span>
        </button>

        {user.is_locked && (
          <button
            className="user-action-item"
            onClick={() => {
              onUnlock();
              setIsOpen(false);
            }}
          >
            <Unlock size={14} />
            <span>{t('users.actions.unlock')}</span>
          </button>
        )}

        {user.mfa_enabled && (
          <button
            className="user-action-item user-action-item-warning"
            onClick={() => {
              onDisableMFA();
              setIsOpen(false);
            }}
          >
            <ShieldOff size={14} />
            <span>{t('users.actions.disableMfa')}</span>
          </button>
        )}

        <div className="user-action-divider" />

        <button
          className="user-action-item user-action-item-danger"
          onClick={() => {
            onDelete();
            setIsOpen(false);
          }}
        >
          <Trash2 size={14} />
          <span>{t('users.actions.deactivate')}</span>
        </button>
      </PortalDropdown>
    </div>
  );
};

const formatDate = (dateStr: string | null): string => {
  if (!dateStr) return '-';
  const date = new Date(dateStr);
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const UserTable = ({
  users,
  isLoading,
  onEdit,
  onDelete,
  onResetPassword,
  onUnlock,
  onRevokeSessions,
  onDisableMFA,
}: UserTableProps) => {
  const { t } = useTranslation();

  if (isLoading) {
    return (
      <div className="admin-empty">
        <div className="admin-spinner admin-spinner-lg" />
        <p className="admin-empty-text">{t('users.loading')}</p>
      </div>
    );
  }

  if (users.length === 0) {
    return (
      <div className="admin-empty">
        <div className="admin-empty-icon">
          <X size={48} />
        </div>
        <p className="admin-empty-title">{t('users.empty')}</p>
        <p className="admin-empty-text">{t('users.emptyHint')}</p>
      </div>
    );
  }

  return (
    <div className="user-table-wrapper">
      <table className="admin-table">
        <thead>
          <tr>
            <th>{t('users.columns.username')}</th>
            <th>{t('users.columns.email')}</th>
            <th>{t('users.columns.roles')}</th>
            <th>{t('users.columns.status')}</th>
            <th>{t('users.columns.mfa')}</th>
            <th>{t('users.columns.lastLogin')}</th>
            <th style={{ width: '60px' }}>{t('users.columns.actions')}</th>
          </tr>
        </thead>
        <tbody>
          {users.map((user) => (
            <tr key={user.id}>
              <td>
                <span className="user-username">
                  {user.username || <span style={{ color: 'var(--admin-text-muted)' }}>—</span>}
                </span>
              </td>
              <td>
                <div className="user-email-cell">
                  <span className="user-email">{user.email}</span>
                  {user.is_locked && (
                    <span className="admin-badge admin-badge-error">
                      {t('users.status.locked')}
                    </span>
                  )}
                </div>
              </td>
              <td>
                <div className="user-roles">
                  {user.roles.map((role) => (
                    <span
                      key={role}
                      className={`admin-badge ${
                        role === 'admin'
                          ? 'admin-badge-info'
                          : role === 'guest'
                            ? 'admin-badge-warning'
                            : 'admin-badge-neutral'
                      }`}
                    >
                      {role}
                    </span>
                  ))}
                </div>
              </td>
              <td>
                {user.is_active ? (
                  <span className="user-status user-status-active">
                    <Check size={14} />
                    {t('users.status.active')}
                  </span>
                ) : (
                  <span className="user-status user-status-inactive">
                    <X size={14} />
                    {t('users.status.inactive')}
                  </span>
                )}
              </td>
              <td>
                {user.mfa_enabled ? (
                  <span className="admin-badge admin-badge-success">{t('common.enabled')}</span>
                ) : (
                  <span className="admin-badge admin-badge-neutral">{t('common.disabled')}</span>
                )}
              </td>
              <td>
                <span className="user-date">{formatDate(user.last_login)}</span>
              </td>
              <td>
                <ActionMenu
                  user={user}
                  onEdit={() => onEdit(user)}
                  onDelete={() => onDelete(user)}
                  onResetPassword={() => onResetPassword(user)}
                  onUnlock={() => onUnlock(user)}
                  onRevokeSessions={() => onRevokeSessions(user)}
                  onDisableMFA={() => onDisableMFA(user)}
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <style>{`
        .user-table-wrapper {
          overflow-x: auto;
        }

        .user-email-cell {
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }

        .user-username {
          font-family: 'SF Mono', 'Monaco', 'Courier New', monospace;
          font-size: 0.875rem;
          color: var(--admin-text);
        }

        .user-email {
          font-weight: 500;
        }

        .user-roles {
          display: flex;
          flex-wrap: wrap;
          gap: 0.375rem;
        }

        .user-status {
          display: inline-flex;
          align-items: center;
          gap: 0.375rem;
          font-size: 0.8125rem;
        }

        .user-status-active {
          color: var(--admin-success);
        }

        .user-status-inactive {
          color: var(--admin-text-muted);
        }

        .user-date {
          font-size: 0.8125rem;
          color: var(--admin-text-muted);
        }

        .user-actions-menu {
          position: relative;
        }

        .user-actions-dropdown {
          position: absolute;
          top: 100%;
          right: 0;
          min-width: 180px;
          padding: 0.5rem;
          background: var(--admin-card-bg-solid);
          border: 1px solid var(--admin-card-border);
          border-radius: var(--admin-radius);
          box-shadow: var(--admin-card-shadow);
          z-index: 50;
          animation: fadeIn 0.15s ease;
        }

        .user-action-item {
          display: flex;
          align-items: center;
          gap: 0.625rem;
          width: 100%;
          padding: 0.5rem 0.75rem;
          font-size: 0.8125rem;
          color: var(--admin-text);
          background: transparent;
          border: none;
          border-radius: var(--admin-radius-sm);
          cursor: pointer;
          transition: background 0.15s ease;
          text-align: left;
        }

        .user-action-item:hover {
          background: hsla(220, 25%, 25%, 0.5);
        }

        .user-action-item-warning {
          color: var(--admin-warning);
        }

        .user-action-item-danger {
          color: var(--admin-error);
        }

        .user-action-divider {
          height: 1px;
          margin: 0.5rem 0;
          background: var(--admin-table-border);
        }
      `}</style>
    </div>
  );
};

export default UserTable;
