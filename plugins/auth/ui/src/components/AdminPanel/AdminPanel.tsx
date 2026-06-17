/**
 * Admin Panel - Main Component
 *
 * Tab-based navigation for user management, sessions, and audit log.
 */

import { useState } from 'react';
import {
  Users,
  Key,
  Activity,
  LogOut,
  Shield,
  Lock,
  Users2,
  ShieldCheck,
  UserCog,
  Globe,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../../hooks/useAuthContext';
import MfaSecurityModal from '../security/MfaSecurityModal';
import type { TabType } from '../../types';
import UsersTab from '../tabs/UsersTab';
import SessionsTab from '../tabs/SessionsTab';
import AuditTab from '../tabs/AuditTab';
import RolesTab from '../tabs/RolesTab';
import GroupsTab from '../tabs/GroupsTab';
import AccessTab from '../tabs/AccessTab';
import SsoTab from '../tabs/SsoTab';
import LanguageSwitcher from '../ui/LanguageSwitcher';
import AuthLogo from '../ui/AuthLogo';
import './AdminPanel.css';

const AdminPanel = () => {
  const [activeTab, setActiveTab] = useState<TabType>('users');
  const [showSecurity, setShowSecurity] = useState(false);
  const { logout, user } = useAuth();
  const { t } = useTranslation();

  const handleLogout = async () => {
    try {
      await logout();
      window.location.href = '/auth/login';
    } catch (err) {
      console.error('Logout failed:', err);
    }
  };

  return (
    <div className="admin-layout">
      {/* Background glow + drifting aurora */}
      <div className="admin-bg-glow" />
      <div className="aurora" aria-hidden="true" />

      {/* Header */}
      <header className="admin-header">
        <div className="admin-header-left">
          <div className="admin-logo">
            <AuthLogo size={28} />
            <span className="admin-logo-text">{t('nav.adminPanel')}</span>
          </div>

          <nav className="admin-tabs">
            <button
              className={`admin-tab ${activeTab === 'users' ? 'active' : ''}`}
              onClick={() => setActiveTab('users')}
            >
              <Users size={16} />
              <span>{t('nav.users')}</span>
            </button>
            <button
              className={`admin-tab ${activeTab === 'roles' ? 'active' : ''}`}
              onClick={() => setActiveTab('roles')}
            >
              <Shield size={16} />
              <span>{t('nav.roles')}</span>
            </button>
            <button
              className={`admin-tab ${activeTab === 'groups' ? 'active' : ''}`}
              onClick={() => setActiveTab('groups')}
            >
              <Users2 size={16} />
              <span>{t('nav.groups')}</span>
            </button>
            <button
              className={`admin-tab ${activeTab === 'access' ? 'active' : ''}`}
              onClick={() => setActiveTab('access')}
            >
              <Lock size={16} />
              <span>{t('nav.access')}</span>
            </button>
            <button
              className={`admin-tab ${activeTab === 'sessions' ? 'active' : ''}`}
              onClick={() => setActiveTab('sessions')}
            >
              <Key size={16} />
              <span>{t('nav.sessions')}</span>
            </button>
            <button
              className={`admin-tab ${activeTab === 'audit' ? 'active' : ''}`}
              onClick={() => setActiveTab('audit')}
            >
              <Activity size={16} />
              <span>{t('nav.audit')}</span>
            </button>
            <button
              className={`admin-tab ${activeTab === 'sso' ? 'active' : ''}`}
              onClick={() => setActiveTab('sso')}
            >
              <Globe size={16} />
              <span>{t('nav.sso')}</span>
            </button>
          </nav>
        </div>

        <div className="admin-header-right">
          <LanguageSwitcher />
          {user && <span className="admin-user-email">{user.email}</span>}
          <a
            className="admin-btn admin-btn-ghost admin-btn-icon"
            href="/auth/account"
            title={t('nav.myAccount')}
          >
            <UserCog size={18} />
          </a>
          <button
            className="admin-btn admin-btn-ghost admin-btn-icon"
            onClick={() => setShowSecurity(true)}
            title={t('security.mfa.title')}
            style={{ color: user?.mfa_enabled ? 'var(--admin-success)' : undefined }}
          >
            {user?.mfa_enabled ? <ShieldCheck size={18} /> : <Shield size={18} />}
          </button>
          <button
            className="admin-btn admin-btn-ghost admin-btn-icon"
            onClick={handleLogout}
            title={t('nav.logout')}
          >
            <LogOut size={18} />
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="admin-main">
        {activeTab === 'users' && <UsersTab />}
        {activeTab === 'roles' && <RolesTab />}
        {activeTab === 'groups' && <GroupsTab />}
        {activeTab === 'access' && <AccessTab />}
        {activeTab === 'sessions' && <SessionsTab />}
        {activeTab === 'audit' && <AuditTab />}
        {activeTab === 'sso' && <SsoTab />}
      </main>

      {/* Footer */}
      <footer className="admin-footer">
        <AuthLogo size={16} />
        <h1 className="baselith-brand" style={{ margin: 0 }}>
          BaselithCore<span className="baselith-brand-dot">.</span>
        </h1>
        <span>{t('nav.version')}</span>
      </footer>

      {showSecurity && <MfaSecurityModal onClose={() => setShowSecurity(false)} />}
    </div>
  );
};

export default AdminPanel;
