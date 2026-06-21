import { useTranslation } from 'react-i18next';
import { motion } from 'motion/react';
import {
  LayoutGrid,
  ScrollText,
  TerminalSquare,
  Sun,
  Moon,
  Shield,
  User,
  LogOut,
} from 'lucide-react';
import { setLanguage } from '@/i18n';
import { logout } from '@/lib/api';
import { spring } from '@/lib/motion';
import { BrandMark } from '@/components/widgets/BrandMark';
import { Clock } from '@/components/Shell/Clock';
import { TenantSwitcher } from '@/components/Shell/TenantSwitcher';
import { useControlStore } from '@/store/useControlStore';
import { useCanAccessTab } from '@/hooks/useAccess';
import { useTheme } from '@/store/useTheme';

const NAV = [
  { id: 'dashboard', icon: LayoutGrid, label: 'nav.overview' },
  { id: 'events', icon: ScrollText, label: 'nav.events' },
  { id: 'system', icon: TerminalSquare, label: 'nav.system' },
] as const;

export function Topbar() {
  const { t, i18n } = useTranslation();
  const currentTab = useControlStore((s) => s.currentTab);
  const setTab = useControlStore((s) => s.setTab);
  const select = useControlStore((s) => s.select);
  const selected = useControlStore((s) => s.selected);
  const me = useControlStore((s) => s.me);
  const connected = useControlStore((s) => s.connected);
  const eventsCount = useControlStore((s) => s.events.length);
  const theme = useTheme((s) => s.theme);
  const toggleTheme = useTheme((s) => s.toggle);
  const canAccessTab = useCanAccessTab();

  // Hide nav entries the central RBAC policy denies for this caller.
  const nav = NAV.filter((item) => canAccessTab(item.id));

  const go = (id: (typeof NAV)[number]['id']) => {
    select(null);
    setTab(id);
  };

  return (
    <header className="topbar sticky top-0 z-10">
      <div className="mx-auto flex h-16 w-full max-w-[1400px] items-center gap-4 px-4 sm:px-6 lg:px-8">
        {/* Brand */}
        <button
          type="button"
          onClick={() => go('dashboard')}
          className="flex shrink-0 items-center gap-2.5"
          title="BaselithControl"
        >
          <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--accent-soft)] accent-ring">
            <BrandMark className="h-4 w-4 t-accent" />
          </span>
          {/* Brand wordmark — product name (untranslated) with an accent dot
              echoing the logo mark, in the same display font. */}
          <span className="hidden font-display text-[15px] font-bold tracking-tight t-primary sm:block">
            BaselithControl<span className="t-accent">.</span>
          </span>
        </button>

        {/* Primary nav */}
        <nav className="ml-1 flex items-center gap-1">
          {nav.map(({ id, icon: Icon, label }) => {
            const active = !selected && currentTab === id;
            return (
              <button
                key={id}
                type="button"
                onClick={() => go(id)}
                aria-current={active ? 'page' : undefined}
                className={`relative flex items-center gap-2 rounded-lg px-3 py-2 text-[13px] font-semibold transition-colors ${
                  active ? 't-accent' : 'nav-item'
                }`}
              >
                {active && (
                  <motion.span
                    layoutId="nav-pill"
                    transition={spring}
                    className="absolute inset-0 rounded-lg bg-[var(--accent-soft)] accent-ring"
                  />
                )}
                <Icon className="relative z-10 h-4 w-4 shrink-0" />
                <span className="relative z-10 hidden sm:block">{t(label)}</span>
                {id === 'events' && eventsCount > 0 && (
                  <span className="relative z-10 rounded-md bg-[var(--accent-soft)] px-1.5 py-0.5 font-mono text-[10px] font-bold tabular-nums t-accent">
                    {eventsCount > 99 ? '99+' : eventsCount}
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        <div className="ml-auto flex items-center gap-2">
          {/* Tenant switcher — only shown when the user belongs to >1 tenant */}
          <TenantSwitcher />

          {/* Wall clock — operator-local time + date */}
          <Clock />

          {/* Live status */}
          <span
            className="hidden items-center gap-1.5 rounded-lg border brd bg-[var(--surface-inset)] px-2.5 py-1.5 text-[12px] font-medium t-dim md:inline-flex"
            title={connected ? t('status.live') : t('status.offline')}
          >
            <span
              className={`led ${connected ? 'status-pulse text-emerald-500' : 'text-amber-500'}`}
            />
            {connected ? t('status.live') : t('status.offline')}
          </span>

          {/* Language */}
          <div className="hidden overflow-hidden rounded-lg border brd text-[11px] font-semibold sm:flex">
            {(['en', 'it'] as const).map((lng) => (
              <button
                key={lng}
                type="button"
                onClick={() => setLanguage(lng)}
                className={`px-2.5 py-1.5 uppercase transition ${
                  i18n.language.startsWith(lng)
                    ? 'bg-[var(--accent-soft)] t-accent'
                    : 't-dim hover:bg-[var(--surface-2)]'
                }`}
              >
                {lng}
              </button>
            ))}
          </div>

          {/* Theme */}
          <button
            type="button"
            onClick={toggleTheme}
            aria-label={t(theme === 'dark' ? 'theme.light' : 'theme.dark')}
            title={t(theme === 'dark' ? 'theme.light' : 'theme.dark')}
            className="control-icon-button"
          >
            {theme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </button>

          {/* User */}
          {me && me.authenticated && (
            <div className="flex shrink-0 items-center gap-2 rounded-lg border brd bg-[var(--surface-inset)] px-2 py-1.5">
              <span
                className={`flex h-6 w-6 items-center justify-center rounded-md ${
                  me.is_admin ? 'bg-[var(--accent-soft)] t-accent' : 'surf t-dim'
                }`}
              >
                {me.is_admin ? (
                  <Shield className="h-3.5 w-3.5" />
                ) : (
                  <User className="h-3.5 w-3.5" />
                )}
              </span>
              <div className="hidden text-left leading-tight lg:block">
                <div className="text-[12px] font-semibold t-primary">
                  {me.display_name || me.username || me.email || me.user_id}
                </div>
                <div className="text-[10px] font-medium t-faint">
                  {me.is_admin ? t('access.admin') : t('access.read_only')}
                </div>
              </div>
              <button
                type="button"
                onClick={() => logout()}
                aria-label={t('access.logout')}
                title={t('access.logout')}
                className="control-icon-button ml-0.5"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
