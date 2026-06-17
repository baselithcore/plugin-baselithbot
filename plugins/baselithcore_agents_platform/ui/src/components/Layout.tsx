import type { ReactNode } from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '@auth';
import { NAV, PLUGIN } from '../nav';

/** Inline logout glyph (lucide-react is not a dependency of this UI). */
function LogOutIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
      <polyline points="16 17 21 12 16 7" />
      <line x1="21" y1="12" x2="9" y2="12" />
    </svg>
  );
}

/** Authenticated-user badge + logout, shown only when a session exists. */
function UserBadge() {
  const { user, logout } = useAuth();
  if (!user) return null;
  return (
    <div className="mb-4 flex items-center justify-between gap-2 rounded-lg bg-ink-700/40 px-3 py-2">
      <span className="truncate text-xs font-medium text-slate-300" title={user.email}>
        {user.username || user.email}
      </span>
      <button
        type="button"
        onClick={() => void logout()}
        title="Logout"
        aria-label="Logout"
        className="shrink-0 rounded-md p-1 text-slate-400 transition-colors hover:bg-ink-700/60 hover:text-slate-100"
      >
        <LogOutIcon />
      </button>
    </div>
  );
}

interface LayoutProps {
  children: ReactNode;
}

/** App shell: animated aurora backdrop, glass sidebar, content column. */
export function Layout({ children }: LayoutProps) {
  // Hide sidebar entries the central RBAC policy denies for this caller.
  const { canAccessTab } = useAuth();
  const nav = NAV.filter((item) => canAccessTab(item.id, PLUGIN));
  return (
    <div className="relative min-h-screen overflow-hidden">
      <div className="aurora" />
      <div className="relative z-10 mx-auto flex max-w-7xl gap-6 px-4 py-6 md:px-8">
        <aside className="hidden w-56 shrink-0 md:block">
          <div className="glass sticky top-6 rounded-2xl p-4 shadow-glass">
            <div className="mb-6 px-2">
              <div className="text-sm font-semibold tracking-tight text-slate-100">
                Agents Platform
              </div>
              <div className="bg-gradient-to-r from-iris to-cyan bg-clip-text text-xs font-medium text-transparent">
                BaselithCore
              </div>
            </div>
            <UserBadge />
            <nav className="flex flex-col gap-1">
              {nav.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) =>
                    [
                      'rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                      isActive
                        ? 'bg-iris/15 text-slate-100 shadow-glow'
                        : 'text-slate-400 hover:bg-ink-700/60 hover:text-slate-200',
                    ].join(' ')
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>
          </div>
        </aside>
        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  );
}
