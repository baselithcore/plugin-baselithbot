import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { motion } from 'motion/react';
import { Moon, Sun, Network, Search, ChevronRight, LogOut } from 'lucide-react';
import { useAuth } from '@auth';
import { useBrain } from '@/store';
import { api } from '@/lib/api';
import { cn } from '@/lib/cn';
import { Kbd, MOD } from './Kbd';
import { MoreMenu } from './MoreMenu';
import { LanguageSwitcher } from './LanguageSwitcher';
import { TagsEditor } from './TagsEditor';
import type { NoteMeta } from '@/lib/types';

/** Note title + tags editor and global controls (theme, graph, palette). */
export function Topbar() {
  const { t } = useTranslation();
  const { user, logout } = useAuth();
  const active = useBrain((s) => s.active);
  const notes = useBrain((s) => s.notes);
  const openNote = useBrain((s) => s.openNote);
  const theme = useBrain((s) => s.theme);
  const toggleTheme = useBrain((s) => s.toggleTheme);
  const toggleGraph = useBrain((s) => s.toggleGraph);
  const setPalette = useBrain((s) => s.setPalette);
  const applyServerNote = useBrain((s) => s.applyServerNote);

  const [title, setTitle] = useState(active?.title ?? '');
  useEffect(() => setTitle(active?.title ?? ''), [active?.id, active?.title]);

  // Ancestor chain (root → parent) for the breadcrumb trail.
  const ancestors = useMemo(() => {
    if (!active) return [] as NoteMeta[];
    const byId = new Map(notes.map((n) => [n.id, n]));
    const chain: NoteMeta[] = [];
    const seen = new Set<string>();
    let pid = byId.get(active.id)?.parent ?? null;
    while (pid && !seen.has(pid)) {
      const meta = byId.get(pid);
      if (!meta) break;
      seen.add(pid);
      chain.unshift(meta);
      pid = meta.parent;
    }
    return chain;
  }, [active, notes]);

  const commitTitle = async () => {
    if (!active || title.trim() === active.title || !title.trim()) {
      setTitle(active?.title ?? '');
      return;
    }
    const saved = await api.updateNote(active.id, { title: title.trim() });
    applyServerNote(saved);
  };

  return (
    <header className="bb-glass-faint flex items-center gap-3 border-b border-[var(--color-border)] px-5 py-3">
      <div className="flex min-w-0 flex-1 flex-col">
        {ancestors.length > 0 && (
          <nav className="flex items-center gap-0.5 text-xs text-[var(--color-faint)]">
            {ancestors.map((a) => (
              <span key={a.id} className="flex items-center gap-0.5">
                <button
                  onClick={() => void openNote(a.id)}
                  className="max-w-[12rem] truncate transition-colors hover:text-[var(--color-accent)]"
                >
                  {a.title}
                </button>
                <ChevronRight className="size-3" />
              </span>
            ))}
          </nav>
        )}
        <input
          value={title}
          disabled={!active}
          onChange={(e) => setTitle(e.target.value)}
          onBlur={commitTitle}
          onKeyDown={(e) => e.key === 'Enter' && (e.target as HTMLInputElement).blur()}
          placeholder={t('topbar.untitled')}
          className="min-w-0 bg-transparent text-xl font-semibold tracking-tight outline-none placeholder:text-[var(--color-faint)]"
        />
      </div>
      {active ? <TagsEditor /> : null}
      <div className="flex items-center gap-1">
        <IconBtn label={t('topbar.search')} onClick={() => setPalette(true)}>
          <Search className="size-4" />
          <Kbd keys={`${MOD}K`} className="ml-1 hidden sm:inline-flex" />
        </IconBtn>
        <IconBtn label={t('topbar.graph')} onClick={toggleGraph}>
          <Network className="size-4" />
        </IconBtn>
        <IconBtn label={t('topbar.theme')} onClick={toggleTheme}>
          {theme === 'dark' ? <Sun className="size-4" /> : <Moon className="size-4" />}
        </IconBtn>
        <LanguageSwitcher />
        <MoreMenu />
        {user && (
          <div className="ml-1 flex items-center gap-1 border-l border-[var(--color-border)] pl-2">
            <span
              className="max-w-[10rem] truncate text-xs font-medium text-[var(--color-muted)]"
              title={user.email}
            >
              {user.username || user.email}
            </span>
            <IconBtn label={t('topbar.logout')} onClick={() => void logout()}>
              <LogOut className="size-4" />
            </IconBtn>
          </div>
        )}
      </div>
    </header>
  );
}

function IconBtn({
  children,
  label,
  onClick,
}: {
  children: React.ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <motion.button
      title={label}
      onClick={onClick}
      whileTap={{ scale: 0.92 }}
      className={cn(
        'flex items-center rounded-xl px-2 py-1.5 text-[var(--color-muted)] transition-colors',
        'hover:bg-[var(--color-elevated)] hover:text-[var(--color-text)]'
      )}
    >
      {children}
    </motion.button>
  );
}
