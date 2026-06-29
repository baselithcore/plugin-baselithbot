/**
 * Admin Console — shell.
 *
 * A dark navigation rail + contextual top bar wrap the management surfaces,
 * styled like a modern identity console (Auth0 / Cloudflare). Visual identity is
 * token-driven via the `.console` wrapper, which re-themes light/dark without
 * touching the shared `@auth/login` wall. Tab bodies are unchanged — they adopt
 * the new look through the shared `.admin-*` classes.
 */

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Sun, Moon, Monitor, UserCog, LogOut } from 'lucide-react';
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
import TenantsTab from '../tabs/TenantsTab';
import BudgetTab from '../tabs/BudgetTab';
import PluginsTab from '../tabs/PluginsTab';
import OverviewTab from '../tabs/OverviewTab';
import UsageOverlay from '../account/UsageOverlay';
import Sidebar from './Sidebar';
import Topbar from './Topbar';
import CommandPalette from './CommandPalette';
import type { PaletteAction } from './CommandPalette';
import { useTheme } from './useTheme';
import './AdminPanel.css';

const COLLAPSE_KEY = 'auth_sidebar_collapsed';

const TAB_BODIES: Record<TabType, React.ComponentType> = {
  overview: OverviewTab,
  users: UsersTab,
  roles: RolesTab,
  groups: GroupsTab,
  access: AccessTab,
  sessions: SessionsTab,
  audit: AuditTab,
  sso: SsoTab,
  tenants: TenantsTab,
  budget: BudgetTab,
  plugins: PluginsTab,
};

const AdminPanel = () => {
  const { t } = useTranslation();
  const { logout } = useAuth();
  const { resolved, setTheme, toggle } = useTheme();

  const [activeTab, setActiveTab] = useState<TabType>('overview');
  const [showSecurity, setShowSecurity] = useState(false);
  const [paletteOpen, setPaletteOpen] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem(COLLAPSE_KEY) === '1');

  const toggleCollapse = useCallback(() => {
    setCollapsed((c) => {
      const next = !c;
      localStorage.setItem(COLLAPSE_KEY, next ? '1' : '0');
      return next;
    });
  }, []);

  // Global ⌘K / Ctrl-K opens the command palette.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setPaletteOpen((v) => !v);
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const handleLogout = useCallback(async () => {
    try {
      await logout();
    } finally {
      window.location.href = '/auth/login';
    }
  }, [logout]);

  const paletteActions = useMemo<PaletteAction[]>(
    () => [
      {
        id: 'theme-toggle',
        label: resolved === 'dark' ? t('theme.light') : t('theme.dark'),
        icon: resolved === 'dark' ? Sun : Moon,
        run: toggle,
      },
      {
        id: 'theme-system',
        label: t('theme.system'),
        icon: Monitor,
        run: () => setTheme('system'),
      },
      {
        id: 'account',
        label: t('nav.myAccount'),
        icon: UserCog,
        run: () => {
          window.location.href = '/auth/account';
        },
      },
      { id: 'logout', label: t('nav.logout'), icon: LogOut, run: handleLogout },
    ],
    [resolved, toggle, setTheme, handleLogout, t]
  );

  const Body = TAB_BODIES[activeTab];

  return (
    <div className="console" data-theme={resolved}>
      <UsageOverlay />
      <Sidebar
        activeTab={activeTab}
        onSelect={setActiveTab}
        collapsed={collapsed}
        onToggleCollapse={toggleCollapse}
        mobileOpen={mobileNavOpen}
        onCloseMobile={() => setMobileNavOpen(false)}
      />

      <div className="console-shell">
        <Topbar
          activeTab={activeTab}
          onOpenPalette={() => setPaletteOpen(true)}
          onOpenMobileNav={() => setMobileNavOpen(true)}
          onOpenSecurity={() => setShowSecurity(true)}
          resolved={resolved}
          onToggleTheme={toggle}
        />
        <main className="console-main">
          <Body />
        </main>
      </div>

      <CommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        onSelectTab={setActiveTab}
        actions={paletteActions}
      />

      {showSecurity && <MfaSecurityModal onClose={() => setShowSecurity(false)} />}
    </div>
  );
};

export default AdminPanel;
