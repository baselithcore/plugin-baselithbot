import { Link, NavLink } from 'react-router-dom';
import { Icon } from '../ui/Icon';
import type { ReactNode } from 'react';

interface NavItem {
  to: string;
  label: string;
  icon: ReactNode;
  end?: boolean;
}

const PRIMARY_NAV: NavItem[] = [
  { to: '/', label: 'Overview', icon: <Icon.Dashboard size={18} />, end: true },
  { to: '/engagements', label: 'Engagements', icon: <Icon.Folder size={18} /> },
  { to: '/targets', label: 'Targets', icon: <Icon.Target size={18} /> },
  { to: '/scans', label: 'Scans', icon: <Icon.Scans size={18} /> },
  { to: '/findings', label: 'Findings', icon: <Icon.Findings size={18} /> },
  { to: '/binary-analysis', label: 'Binary Analysis', icon: <Icon.Bug size={18} /> },
  { to: '/approvals', label: 'Approvals', icon: <Icon.Inbox size={18} /> },
  { to: '/fleet', label: 'Fleet', icon: <Icon.Server size={18} /> },
  { to: '/graph', label: 'Attack Graph', icon: <Icon.Graph size={18} /> },
];

const SECONDARY_NAV: NavItem[] = [
  { to: '/settings/scope', label: 'Scope & Policy', icon: <Icon.Shield size={18} /> },
];

function NavSection({ title, items }: { title: string; items: NavItem[] }) {
  return (
    <div>
      <p className="mb-2 px-3 text-2xs font-semibold uppercase tracking-[0.14em] text-text-subtle">
        {title}
      </p>
      <nav className="space-y-0.5">
        {items.map((n) => (
          <NavLink
            key={n.to}
            to={n.to}
            end={n.end}
            className={({ isActive }) =>
              `group relative flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-brand/10 text-brand'
                  : 'text-text-secondary hover:bg-bg-overlay hover:text-text-primary'
              }`
            }
          >
            {({ isActive }) => (
              <>
                {isActive && (
                  <span className="absolute left-0 top-1.5 bottom-1.5 w-0.5 rounded-r bg-brand shadow-glow-soft" />
                )}
                <span
                  className={
                    isActive ? 'text-brand' : 'text-text-muted group-hover:text-text-secondary'
                  }
                >
                  {n.icon}
                </span>
                <span>{n.label}</span>
              </>
            )}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}

export function Sidebar() {
  return (
    <aside className="hidden h-full flex-col border-r border-bg-line bg-bg-elevated/80 backdrop-blur-xl lg:flex">
      <div className="flex items-center gap-2.5 px-5 py-4 border-b border-bg-line">
        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="relative grid h-8 w-8 place-items-center rounded-md bg-brand/10 ring-1 ring-brand/30 shadow-glow-soft">
            <span className="font-display text-base font-bold text-brand">R</span>
            <span className="absolute -bottom-0.5 -right-0.5 h-2 w-2 rounded-full bg-sev-critical ring-2 ring-bg-elevated animate-pulse" />
          </div>
          <div className="leading-tight">
            <div className="font-display text-sm font-semibold text-text-primary">RED·AGENT</div>
            <div className="text-2xs text-text-muted">Offensive Security</div>
          </div>
        </Link>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-5 space-y-6">
        <Link to="/scans/new" className="ra-btn ra-btn-primary w-full">
          <Icon.Plus size={14} />
          New operation
        </Link>

        <NavSection title="Workspace" items={PRIMARY_NAV} />
        <NavSection title="Operations" items={SECONDARY_NAV} />
      </div>

      <div className="border-t border-bg-line px-5 py-3">
        <div className="rounded-md border border-status-success/20 bg-status-success/5 px-3 py-2">
          <div className="flex items-center gap-2 text-xs text-status-success">
            <span className="h-1.5 w-1.5 rounded-full bg-status-success animate-pulse" />
            <span className="font-mono">control plane online</span>
          </div>
          <div className="mt-1 text-2xs text-text-muted">Scope gates · audit chain · HITL</div>
        </div>
      </div>
    </aside>
  );
}
