import { AnimatePresence, motion } from 'framer-motion';
import { BookOpen, PanelLeftClose, PanelLeftOpen, Pin, Plus, Search, X } from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { useBranding } from '../contexts/BrandingContext';
import { useDomain } from '../contexts/DomainContext';
import type { Conversation } from '../lib/types';
import { cn } from '../lib/cn';
import { ConvRow } from './sidebar/ConvRow';
import { bucketize, matchesQuery } from './sidebar/buckets';

interface Props {
  open: boolean;
  onToggle: () => void;
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNewChat: () => void;
  /** Quando false il bottone "Nuova conversazione" è nascosto
   *  (utente senza permesso ``conversation.write``). */
  canNewChat?: boolean;
  onDelete?: (id: string) => void;
  onRename?: (id: string, title: string) => void;
  onTogglePin?: (id: string) => void;
}

export function Sidebar({
  open,
  onToggle,
  conversations,
  activeId,
  onSelect,
  onNewChat,
  canNewChat = true,
  onDelete,
  onRename,
  onTogglePin,
}: Props) {
  const [query, setQuery] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  // Latest-state refs so stable callbacks read fresh values without
  // re-creating themselves (and re-rendering all ConvRows).
  const editingIdRef = useRef<string | null>(null);
  const editingTitleRef = useRef('');
  editingIdRef.current = editingId;
  editingTitleRef.current = editingTitle;
  const onRenameRef = useRef(onRename);
  onRenameRef.current = onRename;

  useEffect(() => {
    if (editingId && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editingId]);

  const startEdit = useCallback((c: Conversation) => {
    setEditingId(c.id);
    setEditingTitle(c.title);
  }, []);
  const commitEdit = useCallback(() => {
    const id = editingIdRef.current;
    const cb = onRenameRef.current;
    if (id && cb) {
      const trimmed = editingTitleRef.current.trim();
      if (trimmed) cb(id, trimmed);
    }
    setEditingId(null);
  }, []);
  const cancelEdit = useCallback(() => setEditingId(null), []);

  const filtered = useMemo(
    () => conversations.filter((c) => matchesQuery(c, query.trim())),
    [conversations, query]
  );
  const pinned = useMemo(
    () => filtered.filter((c) => c.pinned).sort((a, b) => b.updatedAt - a.updatedAt),
    [filtered]
  );
  const unpinned = useMemo(() => filtered.filter((c) => !c.pinned), [filtered]);
  const buckets = useMemo(() => bucketize(unpinned), [unpinned]);

  const { config: _config, logoUrl: staticLogoUrl } = useBranding();
  const { branding } = useDomain();
  const appName = branding?.ui?.app_name || _config?.companyName || 'LLM Wiki';
  const tagline = branding?.ui?.tagline || 'chat sul vault';
  // Tenant logo wins over the static one. Bust browser cache on tenant
  // switch by appending the slug — same path, different tenant => fresh fetch.
  const logoUrl = branding?.logo_url
    ? `${branding.logo_url}?t=${branding.tenant?.name ?? 'x'}`
    : staticLogoUrl;

  return (
    <AnimatePresence initial={false}>
      {open && (
        <motion.aside
          key="sidebar"
          initial={{ x: -304, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: -304, opacity: 0 }}
          transition={{ duration: 0.26, ease: [0.16, 1, 0.3, 1] }}
          className={cn(
            'flex h-full w-[19rem] shrink-0 flex-col',
            'border-r border-white/10 bg-[var(--color-sidebar-bg)] text-[var(--color-sidebar-text)] shadow-[inset_-1px_0_rgba(255,255,255,0.04)]'
          )}
        >
          {/* Header */}
          <div className="px-3 py-3">
            <div className="rounded-xl border border-white/10 bg-white/[0.07] px-3 py-2.5 shadow-[0_1px_0_rgba(255,255,255,0.08)]">
              <div className="flex items-center justify-between gap-2">
                <div className="flex min-w-0 items-center gap-2">
                  {logoUrl ? (
                    <img
                      src={logoUrl}
                      alt={appName}
                      className="h-8 w-auto max-w-[10.5rem] shrink object-contain object-left"
                      draggable={false}
                      loading="lazy"
                    />
                  ) : (
                    <>
                      <div
                        className="grid size-8 shrink-0 place-items-center rounded-lg shadow-[var(--shadow-brand)]"
                        style={{
                          background:
                            'linear-gradient(135deg, var(--color-brand) 0%, var(--color-accent) 130%)',
                        }}
                      >
                        <BookOpen size={15} className="text-white" strokeWidth={2.5} />
                      </div>
                      <span className="truncate text-[12px] font-semibold text-white/78">
                        LLM Wiki
                      </span>
                    </>
                  )}
                </div>
                <button
                  onClick={onToggle}
                  className="focus-ring shrink-0 rounded-md p-1.5 opacity-65 transition-colors hover:bg-white/10 hover:opacity-100"
                  aria-label="chiudi sidebar"
                  title="⌘B"
                >
                  <PanelLeftClose size={15} />
                </button>
              </div>

              <div className="mt-2.5 min-w-0 border-t border-white/10 pt-2.5 leading-tight">
                <span
                  className="font-display line-clamp-2 text-[15px] font-extrabold tracking-[-0.01em]"
                  title={appName}
                >
                  {appName}
                </span>
                <span className="mt-0.5 block truncate text-[10px] opacity-70" title={tagline}>
                  {tagline}
                </span>
              </div>
            </div>
          </div>

          {/* New chat — gated da conversation.write. Profilo audit-viewer
              senza la perm non vede il bottone (può comunque leggere le
              conversazioni esistenti). */}
          {canNewChat && (
            <div className="px-3 pt-1">
              <button
                onClick={onNewChat}
                className="focus-ring group inline-flex w-full items-center justify-center gap-2 rounded-lg
                           bg-white px-3 py-2.5 text-sm font-semibold text-[var(--color-sidebar-bg)] shadow-[var(--shadow-sm)]
                           hover:bg-white/92 hover:shadow-[var(--shadow-md)]
                           transition-[background-color,box-shadow,transform] duration-[var(--duration-fast)] active:scale-[0.98]"
              >
                <Plus size={14} strokeWidth={2.5} /> Nuova conversazione
              </button>
            </div>
          )}

          {/* Search */}
          <div className="px-3 pt-3">
            <div className="relative">
              <Search
                size={12}
                className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-white/45"
              />
              <input
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="cerca nelle conversazioni…"
                className="focus-ring w-full rounded-lg border border-white/10 bg-white/[0.08]
                           py-2 pl-8 pr-7 text-[12px] text-white shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]
                           placeholder:text-white/42 hover:border-white/16"
                aria-label="cerca nelle conversazioni"
              />
              {query && (
                <button
                  onClick={() => setQuery('')}
                  className="focus-ring absolute right-2 top-1/2 -translate-y-1/2 rounded p-0.5
                             text-white/50 hover:text-white"
                  aria-label="pulisci ricerca"
                >
                  <X size={11} />
                </button>
              )}
            </div>
          </div>

          {/* Conversations */}
          <div className="mt-3 flex min-h-0 flex-1 flex-col px-3">
            <div className="min-h-0 flex-1 overflow-y-auto pr-1 pb-3">
              {conversations.length === 0 && (
                <div className="px-2 py-6 text-center text-xs italic text-white/50">
                  Nessuna conversazione.
                </div>
              )}
              {conversations.length > 0 && filtered.length === 0 && (
                <div className="px-2 py-6 text-center text-xs italic text-white/50">
                  Nessun risultato per "{query}".
                </div>
              )}

              {pinned.length > 0 && (
                <div className="mb-3">
                  <div className="flex items-center gap-1 px-2 pb-1.5 text-[10px] font-semibold uppercase tracking-[0.08em] text-white/45">
                    <Pin size={9} /> Fissate
                  </div>
                  <div className="flex flex-col gap-1">
                    {pinned.map((c) => {
                      const isEditing = editingId === c.id;
                      return (
                        <ConvRow
                          key={c.id}
                          c={c}
                          isActive={activeId === c.id}
                          isEditing={isEditing}
                          editingTitle={isEditing ? editingTitle : undefined}
                          inputRef={inputRef}
                          setEditingTitle={setEditingTitle}
                          startEdit={startEdit}
                          commitEdit={commitEdit}
                          cancelEdit={cancelEdit}
                          onSelect={onSelect}
                          onDelete={onDelete}
                          onRename={onRename}
                          onTogglePin={onTogglePin}
                        />
                      );
                    })}
                  </div>
                </div>
              )}

              {buckets.map((b) => (
                <div key={b.label} className="mb-3">
                  <div className="px-2 pb-1.5 text-[10px] font-semibold uppercase tracking-[0.08em] text-white/45">
                    {b.label}
                  </div>
                  <div className="flex flex-col gap-1">
                    {b.items.map((c) => {
                      const isEditing = editingId === c.id;
                      return (
                        <ConvRow
                          key={c.id}
                          c={c}
                          isActive={activeId === c.id}
                          isEditing={isEditing}
                          editingTitle={isEditing ? editingTitle : undefined}
                          inputRef={inputRef}
                          setEditingTitle={setEditingTitle}
                          startEdit={startEdit}
                          commitEdit={commitEdit}
                          cancelEdit={cancelEdit}
                          onSelect={onSelect}
                          onDelete={onDelete}
                          onRename={onRename}
                          onTogglePin={onTogglePin}
                        />
                      );
                    })}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between border-t border-white/10 px-4 py-3 text-[10px] text-white/45">
            <span>
              {conversations.length}{' '}
              {conversations.length === 1 ? 'conversazione' : 'conversazioni'}
              {query && filtered.length !== conversations.length && (
                <span> · {filtered.length} filtrate</span>
              )}
            </span>
            <span className="font-mono">v0.1</span>
          </div>
        </motion.aside>
      )}

      {!open && (
        <button
          key="open-tab"
          onClick={onToggle}
          className="fixed top-3 left-3 z-20 focus-ring rounded-md p-2
                     bg-[var(--color-canvas-raised)] border border-[var(--color-border)]
                     text-ink-muted hover:text-ink shadow-[var(--shadow-sm)]"
          aria-label="apri sidebar"
          title="⌘B"
        >
          <PanelLeftOpen size={16} />
        </button>
      )}
    </AnimatePresence>
  );
}
