/**
 * Admin Panel - Main Component
 *
 * Tab-based navigation for user management, sessions, and audit log.
 */

import { useState } from 'react';
import { Users, Key, Activity, LogOut } from 'lucide-react';
import { useAuth } from '../../hooks/useAuthContext';
import type { TabType } from '../../types';
import UsersTab from '../tabs/UsersTab';
import SessionsTab from '../tabs/SessionsTab';
import AuditTab from '../tabs/AuditTab';
import './AdminPanel.css';

interface AuthLogoProps {
  size?: number;
}

function AuthLogo({ size = 80 }: AuthLogoProps) {
  const scaledSize = size || 64;
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 64 64"
      fill="none"
      width={scaledSize}
      height={scaledSize}
    >
      <defs>
        <linearGradient
          id="hydra_grad_admin"
          x1="0"
          y1="0"
          x2="64"
          y2="64"
          gradientUnits="userSpaceOnUse"
        >
          <stop stopColor="#7ee0ff" />
          <stop offset="1" stopColor="#7c8cff" />
        </linearGradient>
        <filter id="glow_admin" x="-10" y="-10" width="84" height="84" filterUnits="userSpaceOnUse">
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
      </defs>
      {/* Background Shield */}
      <path
        d="M32 4L54 12V30C54 44.4 44.6 57.6 32 62C19.4 57.6 10 44.4 10 30V12L32 4Z"
        fill="#04060f"
        stroke="url(#hydra_grad_admin)"
        strokeWidth="2"
      />

      {/* Central Lock/Shield Hexagon */}
      <path d="M32 18L44 25V39L32 46L20 39V25L32 18Z" fill="url(#hydra_grad_admin)" opacity="0.9">
        <animate attributeName="opacity" values="0.7;1;0.7" dur="3s" repeatCount="indefinite" />
      </path>

      {/* Inner Lock Detail */}
      <circle cx="32" cy="30" r="3" fill="#04060f" />
      <rect x="30" y="32" width="4" height="6" rx="1" fill="#04060f" />
    </svg>
  );
}

const AdminPanel = () => {
  const [activeTab, setActiveTab] = useState<TabType>('users');
  const { logout, user } = useAuth();

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
      {/* Background glow effect */}
      <div className="admin-bg-glow" />

      {/* Header */}
      <header className="admin-header">
        <div className="admin-header-left">
          <div className="admin-logo">
            <AuthLogo size={28} />
            <span className="admin-logo-text">ADMIN PANEL</span>
          </div>

          <nav className="admin-tabs">
            <button
              className={`admin-tab ${activeTab === 'users' ? 'active' : ''}`}
              onClick={() => setActiveTab('users')}
            >
              <Users size={16} />
              <span>Users</span>
            </button>
            <button
              className={`admin-tab ${activeTab === 'sessions' ? 'active' : ''}`}
              onClick={() => setActiveTab('sessions')}
            >
              <Key size={16} />
              <span>Sessions</span>
            </button>
            <button
              className={`admin-tab ${activeTab === 'audit' ? 'active' : ''}`}
              onClick={() => setActiveTab('audit')}
            >
              <Activity size={16} />
              <span>Audit Log</span>
            </button>
          </nav>
        </div>

        <div className="admin-header-right">
          {user && <span className="admin-user-email">{user.email}</span>}
          <button
            className="admin-btn admin-btn-ghost admin-btn-icon"
            onClick={handleLogout}
            title="Logout"
          >
            <LogOut size={18} />
          </button>
        </div>
      </header>

      {/* Main Content */}
      <main className="admin-main">
        {activeTab === 'users' && <UsersTab />}
        {activeTab === 'sessions' && <SessionsTab />}
        {activeTab === 'audit' && <AuditTab />}
      </main>

      {/* Footer */}
      <footer className="admin-footer">
        <AuthLogo size={16} />
        <h1 className="baselith-brand" style={{ margin: 0 }}>
          BaselithAuth<span className="baselith-brand-dot">.</span>
        </h1>
        <span>Admin Panel v1.0</span>
      </footer>
    </div>
  );
};

export default AdminPanel;
