/**
 * Users Tab Component
 *
 * User management interface with search, filters, and CRUD operations.
 */

import { useState } from 'react';
import { Plus, Search, RefreshCw, Mail, Users } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../index';
import { useUsers } from '../../hooks';
import PageHeader from '../shared/PageHeader';
import UserTable from '../UserTable';
import InvitationsPanel from './InvitationsPanel';
import InviteUserModal from '../modals/InviteUserModal';
import CreateUserWizard from '../modals/CreateUserWizard';
import EditUserModal from '../modals/EditUserModal';
import ResetPasswordModal from '../modals/ResetPasswordModal';
import ConfirmModal from '../modals/ConfirmModal';
import type { User, CreateUserResponse, ResetPasswordResponse } from '../../types';

const UsersTab = () => {
  const { t } = useTranslation();
  const { user: currentUser, impersonate } = useAuth();
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
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [inviteRefresh, setInviteRefresh] = useState(0);

  // Modal states
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [passwordResetResult, setPasswordResetResult] = useState<ResetPasswordResponse | null>(
    null
  );
  const [confirmAction, setConfirmAction] = useState<{
    type: 'delete' | 'unlock' | 'revoke' | 'mfa' | 'impersonate';
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
      setActionError(err instanceof Error ? err.message : t('users.errors.createFailed'));
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
      setActionError(err instanceof Error ? err.message : t('users.errors.updateFailed'));
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
      setActionError(err instanceof Error ? err.message : t('users.errors.resetFailed'));
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
        case 'impersonate':
          await impersonate(confirmAction.user.id);
          // Land on the control-plane host shell so the admin experiences the
          // app exactly as the impersonated user — only the tabs/actions that
          // user is entitled to are visible (the auth admin console would be an
          // access-denied wall for a non-admin target). A persistent banner +
          // Stop is rendered there by the shell to exit impersonation.
          window.location.href = '/baselithcontrol/';
          return;
      }
      setConfirmAction(null);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : t('users.errors.actionFailed'));
    } finally {
      setActionLoading(false);
    }
  };

  const totalPages = Math.ceil(total / limit);

  return (
    <div className="users-tab">
      <PageHeader
        icon={<Users size={22} />}
        title={t('users.title')}
        subtitle={t('users.subtitle')}
        countLabel={t('users.countLabel', { count: total })}
      />

      {/* Toolbar */}
      <div className="users-toolbar">
        <div className="users-search">
          <div className="users-search-input-wrapper">
            <Search size={16} className="users-search-icon" />
            <input
              type="text"
              placeholder={t('users.searchByEmail')}
              className="admin-input users-search-input"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyPress={handleKeyPress}
            />
          </div>
          <button className="admin-btn admin-btn-secondary" onClick={handleSearch}>
            {t('common.search')}
          </button>
        </div>

        <div className="users-filters">
          <label className="admin-checkbox-label">
            <input type="checkbox" checked={showInactive} onChange={handleToggleInactive} />
            {t('users.showInactive')}
          </label>

          <button
            className="admin-btn admin-btn-ghost admin-btn-icon"
            onClick={() => refresh()}
            title={t('common.refresh')}
          >
            <RefreshCw size={16} />
          </button>
        </div>

        <button className="admin-btn admin-btn-secondary" onClick={() => setShowInviteModal(true)}>
          <Mail size={16} />
          {t('users.invite.button')}
        </button>

        <button className="admin-btn admin-btn-primary" onClick={() => setShowCreateModal(true)}>
          <Plus size={16} />
          {t('users.createUser')}
        </button>
      </div>

      <InvitationsPanel refreshKey={inviteRefresh} />

      {/* Error display */}
      {error && (
        <div className="admin-alert admin-alert-error">
          <span>{t('common.errorLabel', { message: error })}</span>
        </div>
      )}

      {actionError && (
        <div className="admin-alert admin-alert-error">
          <span>{t('common.errorLabel', { message: actionError })}</span>
          <button
            className="admin-btn admin-btn-ghost admin-btn-sm"
            onClick={() => setActionError(null)}
          >
            {t('common.dismiss')}
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
          onImpersonate={(user) => setConfirmAction({ type: 'impersonate', user })}
          currentUserId={currentUser?.id}
        />

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="users-pagination">
            <span className="users-pagination-info">
              {t('users.pagination.showing', {
                from: (page - 1) * limit + 1,
                to: Math.min(page * limit, total),
                total,
              })}
            </span>
            <div className="users-pagination-controls">
              <button
                className="admin-btn admin-btn-ghost admin-btn-sm"
                disabled={page <= 1}
                onClick={() => setPage(page - 1)}
              >
                {t('common.previous')}
              </button>
              <span className="users-pagination-page">
                {t('users.pagination.pageOf', { page, total: totalPages })}
              </span>
              <button
                className="admin-btn admin-btn-ghost admin-btn-sm"
                disabled={page >= totalPages}
                onClick={() => setPage(page + 1)}
              >
                {t('common.next')}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Modals */}
      {showInviteModal && (
        <InviteUserModal
          onClose={() => setShowInviteModal(false)}
          onInvited={() => setInviteRefresh((n) => n + 1)}
        />
      )}

      {showCreateModal && (
        <CreateUserWizard
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
            message: t('users.createdSuccessfully', { email: createdUser.user.email }),
            temporary_password: createdUser.temporary_password,
          }}
          onClose={() => setCreatedUser(null)}
        />
      )}

      {confirmAction && (
        <ConfirmModal
          title={
            confirmAction.type === 'delete'
              ? t('users.confirm.deactivateTitle')
              : confirmAction.type === 'unlock'
                ? t('users.confirm.unlockTitle')
                : confirmAction.type === 'revoke'
                  ? t('users.confirm.revokeTitle')
                  : confirmAction.type === 'impersonate'
                    ? t('users.confirm.impersonateTitle')
                    : t('users.confirm.disableMfaTitle')
          }
          message={
            confirmAction.type === 'delete'
              ? t('users.confirm.deactivateMessage', { email: confirmAction.user.email })
              : confirmAction.type === 'unlock'
                ? t('users.confirm.unlockMessage', { email: confirmAction.user.email })
                : confirmAction.type === 'revoke'
                  ? t('users.confirm.revokeMessage', { email: confirmAction.user.email })
                  : confirmAction.type === 'impersonate'
                    ? t('users.confirm.impersonateMessage', { email: confirmAction.user.email })
                    : t('users.confirm.disableMfaMessage', { email: confirmAction.user.email })
          }
          confirmLabel={
            confirmAction.type === 'delete'
              ? t('users.actions.deactivate')
              : confirmAction.type === 'impersonate'
                ? t('users.actions.impersonate')
                : t('common.confirm')
          }
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
