/**
 * Users Tab Component
 *
 * User management interface with search, filters, and CRUD operations.
 */

import { useState } from 'react';
import { Plus, Search, RefreshCw } from 'lucide-react';
import { useUsers } from '../../hooks';
import UserTable from '../UserTable';
import CreateUserModal from '../modals/CreateUserModal';
import EditUserModal from '../modals/EditUserModal';
import ResetPasswordModal from '../modals/ResetPasswordModal';
import ConfirmModal from '../modals/ConfirmModal';
import type { User, CreateUserResponse, ResetPasswordResponse } from '../../types';

const UsersTab = () => {
  const {
    users,
    total,
    page,
    limit,
    isLoading,
    error,
    refresh,
    createUser,
    updateUser,
    deleteUser,
    resetPassword,
    unlockUser,
    revokeSessions,
    disableMFA,
    setPage,
    setSearch,
    setIncludeInactive,
  } = useUsers();

  const [searchInput, setSearchInput] = useState('');
  const [showInactive, setShowInactive] = useState(false);

  // Modal states
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [passwordResetResult, setPasswordResetResult] = useState<ResetPasswordResponse | null>(
    null
  );
  const [confirmAction, setConfirmAction] = useState<{
    type: 'delete' | 'unlock' | 'revoke' | 'mfa';
    user: User;
  } | null>(null);
  const [createdUser, setCreatedUser] = useState<CreateUserResponse | null>(null);

  // Action states
  const [actionLoading, setActionLoading] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const handleSearch = () => {
    setSearch(searchInput);
    setPage(1);
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  const handleToggleInactive = () => {
    setShowInactive(!showInactive);
    setIncludeInactive(!showInactive);
    setPage(1);
  };

  const handleCreateUser = async (data: Parameters<typeof createUser>[0]) => {
    setActionLoading(true);
    setActionError(null);
    try {
      const result = await createUser(data);
      setShowCreateModal(false);
      if (result.temporary_password) {
        setCreatedUser(result);
      }
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to create user');
      throw err;
    } finally {
      setActionLoading(false);
    }
  };

  const handleUpdateUser = async (userId: string, data: Parameters<typeof updateUser>[1]) => {
    setActionLoading(true);
    setActionError(null);
    try {
      await updateUser(userId, data);
      setEditingUser(null);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to update user');
      throw err;
    } finally {
      setActionLoading(false);
    }
  };

  const handleResetPassword = async (user: User) => {
    setActionLoading(true);
    setActionError(null);
    try {
      const result = await resetPassword(user.id);
      setPasswordResetResult(result);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Failed to reset password');
    } finally {
      setActionLoading(false);
    }
  };

  const handleConfirmAction = async () => {
    if (!confirmAction) return;

    setActionLoading(true);
    setActionError(null);

    try {
      switch (confirmAction.type) {
        case 'delete':
          await deleteUser(confirmAction.user.id);
          break;
        case 'unlock':
          await unlockUser(confirmAction.user.id);
          break;
        case 'revoke':
          await revokeSessions(confirmAction.user.id);
          break;
        case 'mfa':
          await disableMFA(confirmAction.user.id);
          break;
      }
      setConfirmAction(null);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : 'Action failed');
    } finally {
      setActionLoading(false);
    }
  };

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="users-tab">
      {/* Toolbar */}
      <div className="users-toolbar">
        <div className="users-search">
          <div className="users-search-input-wrapper">
            <Search size={16} className="users-search-icon" />
            <input
              type="text"
              placeholder="Search by email..."
              className="admin-input users-search-input"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyPress={handleKeyPress}
            />
          </div>
          <button className="admin-btn admin-btn-secondary" onClick={handleSearch}>
            Search
          </button>
        </div>

        <div className="users-filters">
          <label className="admin-checkbox-label">
            <input type="checkbox" checked={showInactive} onChange={handleToggleInactive} />
            Show inactive
          </label>

          <button
            className="admin-btn admin-btn-ghost admin-btn-icon"
            onClick={() => refresh()}
            title="Refresh"
          >
            <RefreshCw size={16} />
          </button>
        </div>

        <button className="admin-btn admin-btn-primary" onClick={() => setShowCreateModal(true)}>
          <Plus size={16} />
          Create User
        </button>
      </div>

      {/* Error display */}
      {error && (
        <div className="admin-alert admin-alert-error">
          <span>Error: {error}</span>
        </div>
      )}

      {actionError && (
        <div className="admin-alert admin-alert-error">
          <span>Error: {actionError}</span>
          <button
            className="admin-btn admin-btn-ghost admin-btn-sm"
            onClick={() => setActionError(null)}
          >
            Dismiss
          </button>
        </div>
      )}

      {/* User Table */}
      <div className="admin-card">
        <UserTable
          users={users}
          isLoading={isLoading}
          onEdit={setEditingUser}
          onDelete={(user) => setConfirmAction({ type: 'delete', user })}
          onResetPassword={handleResetPassword}
          onUnlock={(user) => setConfirmAction({ type: 'unlock', user })}
          onRevokeSessions={(user) => setConfirmAction({ type: 'revoke', user })}
          onDisableMFA={(user) => setConfirmAction({ type: 'mfa', user })}
        />

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="users-pagination">
            <span className="users-pagination-info">
              Showing {(page - 1) * limit + 1}-{Math.min(page * limit, total)} of {total} users
            </span>
            <div className="users-pagination-controls">
              <button
                className="admin-btn admin-btn-ghost admin-btn-sm"
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
              >
                Previous
              </button>
              <span className="users-pagination-page">
                Page {page} of {totalPages}
              </span>
              <button
                className="admin-btn admin-btn-ghost admin-btn-sm"
                disabled={page >= totalPages}
                onClick={() => setPage(page + 1)}
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Modals */}
      {showCreateModal && (
        <CreateUserModal
          onClose={() => setShowCreateModal(false)}
          onCreate={handleCreateUser}
          isLoading={actionLoading}
        />
      )}

      {editingUser && (
        <EditUserModal
          user={editingUser}
          onClose={() => setEditingUser(null)}
          onUpdate={handleUpdateUser}
          isLoading={actionLoading}
        />
      )}

      {passwordResetResult && (
        <ResetPasswordModal
          result={passwordResetResult}
          onClose={() => setPasswordResetResult(null)}
        />
      )}

      {createdUser && createdUser.temporary_password && (
        <ResetPasswordModal
          result={{
            message: `User ${createdUser.user.email} created successfully`,
            temporary_password: createdUser.temporary_password,
          }}
          onClose={() => setCreatedUser(null)}
        />
      )}

      {confirmAction && (
        <ConfirmModal
          title={
            confirmAction.type === 'delete'
              ? 'Deactivate User'
              : confirmAction.type === 'unlock'
                ? 'Unlock Account'
                : confirmAction.type === 'revoke'
                  ? 'Revoke Sessions'
                  : 'Disable MFA'
          }
          message={
            confirmAction.type === 'delete'
              ? `Are you sure you want to deactivate ${confirmAction.user.email}? They will no longer be able to log in.`
              : confirmAction.type === 'unlock'
                ? `Unlock the account for ${confirmAction.user.email}? This will clear failed login attempts.`
                : confirmAction.type === 'revoke'
                  ? `Revoke all active sessions for ${confirmAction.user.email}? They will be logged out everywhere.`
                  : `Disable MFA for ${confirmAction.user.email}? They will need to set it up again.`
          }
          confirmLabel={confirmAction.type === 'delete' ? 'Deactivate' : 'Confirm'}
          isDanger={confirmAction.type === 'delete' || confirmAction.type === 'mfa'}
          onConfirm={handleConfirmAction}
          onCancel={() => setConfirmAction(null)}
          isLoading={actionLoading}
        />
      )}

      <style>{`
        .users-tab {
          display: flex;
          flex-direction: column;
          gap: 1.25rem;
        }

        .users-toolbar {
          display: flex;
          align-items: center;
          gap: 1rem;
          flex-wrap: wrap;
        }

        .users-search {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          flex: 1;
          min-width: 300px;
        }

        .users-search-input-wrapper {
          position: relative;
          flex: 1;
        }

        .users-search-icon {
          position: absolute;
          left: 0.875rem;
          top: 50%;
          transform: translateY(-50%);
          color: var(--admin-text-subtle);
          pointer-events: none;
        }

        .users-search-input {
          padding-left: 2.5rem;
        }

        .users-filters {
          display: flex;
          align-items: center;
          gap: 1rem;
        }

        .users-pagination {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 1rem 1.25rem;
          border-top: 1px solid var(--admin-table-border);
        }

        .users-pagination-info {
          font-size: 0.8125rem;
          color: var(--admin-text-muted);
        }

        .users-pagination-controls {
          display: flex;
          align-items: center;
          gap: 0.75rem;
        }

        .users-pagination-page {
          font-size: 0.875rem;
          color: var(--admin-text);
        }

        @media (max-width: 768px) {
          .users-toolbar {
            flex-direction: column;
            align-items: stretch;
          }

          .users-search {
            min-width: auto;
          }

          .users-filters {
            justify-content: space-between;
          }
        }
      `}</style>
    </div>
  );
};

export default UsersTab;
