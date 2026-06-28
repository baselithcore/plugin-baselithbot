/**
 * Console top bar — contextual page title, the ⌘K command launcher, theme
 * toggle, language + tenant switchers, and an account/identity menu.
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Menu,
  Search,
  Sun,
  Moon,
  ShieldCheck,
  Shield,
  UserCog,
  LogOut,
  ChevronRight,
} from 'lucide-react';
import { useAuth } from '../../hooks/useAuthContext';
import LanguageSwitcher from '../ui/LanguageSwitcher';
import TenantSwitcher from '../ui/TenantSwitcher';
import { findNavItem, findNavGroup } from './nav';
import type { TabType } from '../../types';
import type { ResolvedTheme } from './useTheme';

interface TopbarProps {
  activeTab: TabType;
  onOpenPalette: () => void;
  onOpenMobileNav: () => void;
  onOpenSecurity: () => void;
  resolved: ResolvedTheme;
  onToggleTheme: () => void;
}

const initialsOf = (email?: string): string =>
  (email ?? '?')
    .replace(/@.*/, '')
    .split(/[.\-_]/)
    .filter(Boolean)
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase())
    .join('') || '?';

const Topbar = ({
  activeTab,
  onOpenPalette,
  onOpenMobileNav,
  onOpenSecurity,
  resolved,
  onToggleTheme,
}: TopbarProps) => {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const item = findNavItem(activeTab);
  const group = findNavGroup(activeTab);

  const handleLogout = async () => {
    try {
      await logout();
    } finally {
      window.location.href = '/auth/login';
    }
  };

  return (
    <header className="tb">
      <div className="tb-left">
        <button
          type="button"
          className="tb-icon tb-burger"
          onClick={onOpenMobileNav}
          aria-label={t('nav.openMenu')}
        >
          <Menu size={18} />
        </button>
        <nav className="tb-crumbs" aria-label="Breadcrumb">
          <span className="tb-crumb-group">{t(group.labelKey)}</span>
          <ChevronRight size={15} className="tb-crumb-sep" aria-hidden="true" />
          <span className="tb-crumb-current" aria-current="page">
            {t(item.labelKey)}
          </span>
        </nav>
      </div>

      <div className="tb-right">
        <button type="button" className="tb-search" onClick={onOpenPalette}>
          <Search size={15} />
          <span>{t('command.openLabel')}</span>
          <kbd className="tb-kbd">⌘K</kbd>
        </button>

        <button
          type="button"
          className="tb-icon"
          onClick={onToggleTheme}
          title={t('theme.toggle')}
          aria-label={t('theme.toggle')}
        >
          {resolved === 'dark' ? <Sun size={17} /> : <Moon size={17} />}
        </button>

        <LanguageSwitcher />
        <TenantSwitcher />

        <button
          type="button"
          className="tb-icon"
          onClick={onOpenSecurity}
          title={t('security.mfa.title')}
          aria-label={t('security.mfa.title')}
          style={{ color: user?.mfa_enabled ? 'var(--admin-success)' : undefined }}
        >
          {user?.mfa_enabled ? <ShieldCheck size={17} /> : <Shield size={17} />}
        </button>

        <div className="tb-user">
          <button
            type="button"
            className="tb-avatar"
            onClick={() => setMenuOpen((v) => !v)}
            aria-haspopup="menu"
            aria-expanded={menuOpen}
          >
            <span className="tb-avatar-badge">{initialsOf(user?.email)}</span>
          </button>
          {menuOpen && (
            <>
              <button
                type="button"
                className="tb-menu-backdrop"
                aria-label={t('common.close')}
                onClick={() => setMenuOpen(false)}
              />
              <div className="tb-menu" role="menu">
                <div className="tb-menu-id">
                  <span className="tb-menu-email">{user?.email}</span>
                  <span className="tb-menu-role">{(user?.roles ?? []).join(' · ') || '—'}</span>
                </div>
                <a className="tb-menu-item" href="/auth/account" role="menuitem">
                  <UserCog size={15} /> {t('nav.myAccount')}
                </a>
                <button
                  type="button"
                  className="tb-menu-item"
                  role="menuitem"
                  onClick={() => {
                    setMenuOpen(false);
                    onOpenSecurity();
                  }}
                >
                  <ShieldCheck size={15} /> {t('security.mfa.title')}
                </button>
                <button
                  type="button"
                  className="tb-menu-item danger"
                  role="menuitem"
                  onClick={handleLogout}
                >
                  <LogOut size={15} /> {t('nav.logout')}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </header>
  );
};

export default Topbar;
