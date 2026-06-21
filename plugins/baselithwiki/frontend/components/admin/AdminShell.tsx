/**
 * AdminShell — layout condiviso pagine admin (`/admin/*`).
 *
 * Top bar minimale con: back-to-app, titolo sezione, tabs (Utenti / Ruoli).
 * Niente sidebar conversazioni: pagine admin sono full-page enterprise,
 * non integrate nel flusso chat.
 */

import { ArrowLeft, Code2, MessageCircleHeart } from 'lucide-react';
import type { ReactNode } from 'react';

import { useAuth } from '../../contexts/AuthContext';
import { LanguageSwitcher } from '../LanguageSwitcher';
import { ThemeToggle } from '../ThemeToggle';
import { navigate } from '../../hooks/useLocation';
import { cn } from '../../lib/cn';

// Users / roles / groups are owned by the central ``auth`` plugin's Access
// Control — the wiki admin shell only exposes its own surfaces (feedback,
// embeds).
type AdminTabId = 'embeds' | 'feedback';

interface Props {
  active: AdminTabId;
  children: ReactNode;
}

interface TabDef {
  id: AdminTabId;
  label: string;
  path: string;
  icon: typeof Code2;
  perm: string;
}

const TABS: TabDef[] = [
  {
    id: 'feedback',
    label: 'Feedback',
    path: '/admin/feedback',
    icon: MessageCircleHeart,
    perm: 'feedback.read',
  },
  {
    id: 'embeds',
    label: 'Widget embed',
    path: '/admin/embeds',
    icon: Code2,
    perm: 'admin.embed.manage',
  },
];

export function AdminShell({ active, children }: Props) {
  const { can } = useAuth();
  // Filtra le tab in base ai permessi del caller: un moderator con
  // solo `feedback.read` non deve vedere tab a cui non ha accesso. La
  // tab attiva è sempre mostrata (il caller ci è già arrivato via
  // route gating, evita flicker se il can() lag-ga il refresh).
  const visibleTabs = TABS.filter((t) => t.id === active || can(t.perm));
  return (
    <div className="flex h-screen w-screen flex-col overflow-hidden bg-canvas text-ink">
      <header className="flex items-center gap-4 border-b border-[var(--color-border)] bg-[var(--color-canvas)]/75 px-4 py-2.5 backdrop-blur-glass">
        <button
          type="button"
          onClick={() => navigate('/')}
          className="btn-secondary"
          title="torna all'app"
          aria-label="Torna all'app"
        >
          <ArrowLeft size={13} aria-hidden />
          <span className="hidden sm:inline">App</span>
        </button>
        <div className="flex flex-col leading-tight">
          <span className="text-[10px] uppercase text-ink-subtle font-medium">Admin</span>
          <span className="text-sm font-semibold">Gestione accessi</span>
        </div>
        <nav className="ml-4 flex items-center gap-1" aria-label="sezioni admin">
          {visibleTabs.map((t) => {
            const Icon = t.icon;
            const isActive = t.id === active;
            return (
              <button
                key={t.id}
                type="button"
                onClick={() => navigate(t.path)}
                className={cn(
                  'inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-xs font-medium transition-colors',
                  isActive
                    ? 'bg-[var(--color-brand-soft)] text-ink'
                    : 'text-ink-subtle hover:bg-[var(--color-surface-hover)] hover:text-ink'
                )}
                aria-current={isActive ? 'page' : undefined}
              >
                <Icon size={13} />
                {t.label}
              </button>
            );
          })}
        </nav>
        <div className="ml-auto flex items-center gap-2">
          <LanguageSwitcher />
          <ThemeToggle />
        </div>
      </header>
      <main className="flex-1 overflow-y-auto">{children}</main>
    </div>
  );
}
