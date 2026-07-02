import { useEffect, useMemo, useRef, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Database,
  Globe,
  Lock,
  PanelLeftClose,
  PlugZap,
  Plus,
  Search,
  SearchX,
  Share2,
  ShieldCheck,
  Trash2,
  Users as UsersIcon,
  X,
} from 'lucide-react';
import { toast } from 'sonner';
import { DIALECT_META, type ConnectionSummary, type DialectKind } from '@dbview/shared';
import { api } from '../lib/api.js';
import { useAppStore } from '../store/app.js';
import { getCurrentUser } from '../lib/auth.js';
import { cn } from '../lib/cn.js';
import { EmptyState } from './ui/EmptyState.js';
import { ConnectionForm } from './connection/ConnectionForm.js';
import { ConnectionSharingDialog } from './ConnectionSharingDialog.js';
import { DialectIcon } from './connection/DialectIcon.js';
import { useDebouncedValue } from '../lib/use-debounced-value.js';

const KIND_ORDER: DialectKind[] = [
  'sql',
  'graph',
  'document',
  'vector',
  'keyvalue',
  'search',
  'saas',
];

const KIND_LABELS: Record<DialectKind, string> = {
  sql: 'Relational',
  graph: 'Graph',
  document: 'Document',
  vector: 'Vector',
  keyvalue: 'Key-value',
  search: 'Search',
  saas: 'SaaS',
};

const SEARCH_DEBOUNCE_MS = 120;
// Below this threshold the list is short enough to scan visually; hiding the
// search bar removes chrome that would feel like noise. Once the install
// grows we surface it.
const SEARCH_VISIBLE_THRESHOLD = 4;

export function ConnectionPanel() {
  const qc = useQueryClient();
  const activeId = useAppStore((s) => s.activeConnectionId);
  const setActive = useAppStore((s) => s.setActiveConnection);
  const me = getCurrentUser();
  const isAdmin = me?.role === 'admin';

  const conns = useQuery({ queryKey: ['connections'], queryFn: api.listConnections });
  const [open, setOpen] = useState(false);
  const [filter, setFilter] = useState('');
  const [sharingTarget, setSharingTarget] = useState<ConnectionSummary | null>(null);
  const setLeftCollapsed = useAppStore((s) => s.setLeftCollapsed);

  // Run the actual filter against a debounced value so each keystroke stays
  // cheap (the panel re-renders on every change of `filter` for the input UI,
  // but the heavier `groupedConnections` recompute reads `debouncedFilter`).
  const debouncedFilter = useDebouncedValue(filter, SEARCH_DEBOUNCE_MS);
  const searchInputRef = useRef<HTMLInputElement>(null);

  const total = conns.data?.length ?? 0;
  // Keep the search bar mounted once it has appeared so removing a connection
  // mid-typing does not yank the input from under the user.
  const searchVisible = total >= SEARCH_VISIBLE_THRESHOLD || filter.length > 0;

  // ⌘/Ctrl + F focuses the search box — panel-scoped, doesn't fight the global
  // ⌘K command palette. Skip when search bar is hidden (too few connections).
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (!searchVisible) return;
      if (!(e.metaKey || e.ctrlKey) || e.key.toLowerCase() !== 'f') return;
      const tag = (e.target as HTMLElement | null)?.tagName;
      const editable =
        tag === 'INPUT' ||
        tag === 'TEXTAREA' ||
        (e.target as HTMLElement | null)?.isContentEditable;
      if (editable && document.activeElement !== searchInputRef.current) return;
      e.preventDefault();
      searchInputRef.current?.focus();
      searchInputRef.current?.select();
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [searchVisible]);

  const create = useMutation({
    mutationFn: api.createConnection,
    onSuccess: (c) => {
      qc.invalidateQueries({ queryKey: ['connections'] });
      setActive(c.id);
      setOpen(false);
      toast.success(`Connected to ${c.name}`, { description: c.displayDatabase });
    },
    onError: (err: Error) => toast.error('Connection failed', { description: err.message }),
  });

  const test = useMutation({
    mutationFn: api.testConnection,
    onSuccess: () => toast.success('Connection OK'),
    onError: (err: Error) => toast.error('Connection test failed', { description: err.message }),
  });

  const del = useMutation({
    mutationFn: api.deleteConnection,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['connections'] });
      toast.success('Connection removed');
    },
  });

  const groupedConnections = useMemo(() => {
    const normalized = debouncedFilter.trim().toLowerCase();
    const groups = new Map<DialectKind, ConnectionSummary[]>();

    for (const c of conns.data ?? []) {
      if (normalized && !connectionMatches(c, normalized)) continue;
      const kind = DIALECT_META[c.dialect].kind;
      const items = groups.get(kind) ?? [];
      items.push(c);
      groups.set(kind, items);
    }

    return KIND_ORDER.map((kind) => {
      const items = groups.get(kind) ?? [];
      items.sort((a, b) => compareConnections(a, b, activeId));
      return { kind, label: KIND_LABELS[kind], connections: items };
    }).filter((group) => group.connections.length > 0);
  }, [activeId, conns.data, debouncedFilter]);

  const hasConnections = total > 0;
  const hasVisibleConnections = groupedConnections.length > 0;
  const matchCount = groupedConnections.reduce((n, g) => n + g.connections.length, 0);

  const onSearchKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Escape') {
      if (filter.length > 0) {
        e.preventDefault();
        e.stopPropagation();
        setFilter('');
      } else {
        searchInputRef.current?.blur();
      }
      return;
    }
    if (e.key === 'Enter') {
      // First visible match becomes active — common autocomplete UX.
      e.preventDefault();
      const first = groupedConnections[0]?.connections[0];
      if (first) setActive(first.id);
    }
  };

  return (
    <div data-tour="connections-panel" className="panel flex flex-col h-full min-h-0">
      <div className="panel-header">
        <div className="flex items-center gap-2 text-[13px] font-semibold">
          <Database className="w-3.5 h-3.5 text-accent" />
          <span>Connections</span>
          {conns.data && (
            <span className="chip h-5 px-1.5 text-[10px] font-mono">{conns.data.length}</span>
          )}
        </div>
        <div className="flex items-center gap-0.5">
          {isAdmin && (
            <button
              className="btn-icon"
              onClick={() => setOpen((v) => !v)}
              aria-label="New connection"
              title="New connection"
            >
              {open ? <X className="w-4 h-4" /> : <Plus className="w-4 h-4" />}
            </button>
          )}
          <button
            className="btn-icon"
            onClick={() => setLeftCollapsed(true)}
            aria-label="Collapse panel"
            title="Collapse panel (⌘[)"
          >
            <PanelLeftClose className="w-4 h-4" />
          </button>
        </div>
      </div>

      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden shrink-0"
          >
            <div className="max-h-[65vh] overflow-y-auto">
              <ConnectionForm
                onSubmit={(dto) => create.mutate(dto)}
                onTest={(dto) => test.mutate(dto)}
                submitting={create.isPending}
                testing={test.isPending}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {searchVisible && (
        <div className="shrink-0 border-b p-2" style={{ borderColor: 'rgb(var(--border-subtle))' }}>
          <div
            className={cn(
              'relative flex items-center rounded-md border bg-[rgb(var(--surface-2)/0.35)] transition-colors focus-within:border-accent/45 focus-within:ring-1 focus-within:ring-accent/25',
              filter.length > 0 && matchCount === 0 && 'border-rose-400/50 ring-1 ring-rose-400/30',
            )}
            style={{ borderColor: 'rgb(var(--border-subtle))' }}
          >
            <Search className="ml-2.5 h-3.5 w-3.5 shrink-0 text-text-dim" aria-hidden />
            <input
              ref={searchInputRef}
              type="search"
              role="searchbox"
              className="flex-1 bg-transparent h-8 px-2 text-[12px] outline-none placeholder:text-text-dim"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              onKeyDown={onSearchKeyDown}
              placeholder="Filter by name, host, database…"
              aria-label="Search connections"
              aria-controls="connections-list"
              spellCheck={false}
              autoCorrect="off"
              autoCapitalize="off"
            />
            {filter ? (
              <>
                <span className="font-mono text-[10px] text-text-dim shrink-0" aria-live="polite">
                  {matchCount}/{total}
                </span>
                <button
                  className="btn-icon mx-1 h-6 w-6 shrink-0"
                  onClick={() => {
                    setFilter('');
                    searchInputRef.current?.focus();
                  }}
                  aria-label="Clear connection search"
                  title="Clear (Esc)"
                >
                  <X className="h-3 w-3" />
                </button>
              </>
            ) : (
              <kbd
                className="mr-2 hidden md:inline-flex items-center gap-0.5 rounded border px-1 py-0 text-[9px] font-mono text-text-dim shrink-0"
                style={{ borderColor: 'rgb(var(--border-subtle))' }}
                aria-hidden
              >
                ⌘F
              </kbd>
            )}
          </div>
        </div>
      )}

      <div className="flex-1 overflow-auto min-h-0">
        {conns.isLoading && (
          <div className="p-3 flex flex-col gap-2">
            {[0, 1, 2].map((i) => (
              <div key={i} className="skeleton h-12" />
            ))}
          </div>
        )}
        {conns.data?.length === 0 && !open && (
          <EmptyState
            icon={<Database className="w-5 h-5" />}
            title="No connections"
            description={
              isAdmin
                ? 'Add a database connection to start exploring.'
                : 'No connections shared with you yet. Ask an admin to share one.'
            }
            action={
              isAdmin ? (
                <button onClick={() => setOpen(true)} className="btn-primary">
                  <Plus className="w-3.5 h-3.5" />
                  New connection
                </button>
              ) : undefined
            }
          />
        )}
        {hasConnections && !hasVisibleConnections && (
          <EmptyState
            icon={<SearchX className="w-5 h-5" />}
            title={`No matches for "${filter.trim()}"`}
            description="Try a different name, host, database, dialect, or sharing mode."
            action={
              <button onClick={() => setFilter('')} className="btn">
                <X className="w-3.5 h-3.5" />
                Clear search
              </button>
            }
          />
        )}
        <div id="connections-list" role="list" className="flex flex-col gap-3 p-2">
          <AnimatePresence initial={false}>
            {groupedConnections.map((group) => (
              <motion.section
                key={group.kind}
                layout
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] }}
                className="flex flex-col gap-1.5"
              >
                <div
                  className="sticky top-0 z-[1] flex items-center justify-between rounded-md px-1.5 py-1 backdrop-blur-md"
                  style={{ background: 'rgb(var(--surface-1) / 0.86)' }}
                >
                  <span className="text-[10px] font-semibold uppercase tracking-wide text-text-dim">
                    {group.label}
                  </span>
                  <span className="chip h-5 px-1.5 text-[10px] font-mono">
                    {group.connections.length}
                  </span>
                </div>
                <div className="flex flex-col gap-1.5">
                  {group.connections.map((c) => {
                    const isActive = activeId === c.id;
                    const meta = DIALECT_META[c.dialect];
                    const location = connectionLocation(c);
                    return (
                      <motion.div
                        key={c.id}
                        layout
                        initial={{ opacity: 0, y: 4, height: 0 }}
                        animate={{ opacity: 1, y: 0, height: 'auto' }}
                        exit={{ opacity: 0, y: -4, height: 0 }}
                        transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
                        onClick={() => setActive(c.id)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            setActive(c.id);
                          }
                        }}
                        role="button"
                        tabIndex={0}
                        aria-pressed={isActive}
                        className={cn(
                          'group relative flex items-start gap-2.5 px-2.5 py-2.5 rounded-md cursor-pointer transition-all border outline-none',
                          isActive
                            ? 'ring-1 ring-accent/30 shadow-sm'
                            : 'hover:bg-surface-2/62 hover:border-border focus-visible:border-accent/45',
                        )}
                        style={{
                          background: isActive
                            ? 'linear-gradient(135deg, rgb(var(--accent) / 0.11), rgb(var(--brand) / 0.055))'
                            : 'rgb(var(--surface-2) / 0.18)',
                          borderColor: isActive
                            ? 'rgb(var(--accent) / 0.3)'
                            : 'rgb(var(--border-subtle) / 0.58)',
                        }}
                      >
                        {isActive && (
                          <span className="absolute left-0 top-2 bottom-2 w-0.5 rounded-r bg-accent bar-in" />
                        )}
                        <div className="mt-0.5 shrink-0">
                          <DialectIcon dialect={c.dialect} size={24} />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-1.5 min-w-0">
                            <span className="text-[13px] font-medium truncate">{c.name}</span>
                            {isActive && (
                              <span className="chip chip-accent h-4 px-1 text-[9px] shrink-0">
                                active
                              </span>
                            )}
                            {isAdmin && <SharingBadge sharing={c.sharing} />}
                          </div>
                          <div className="mt-1 flex items-center gap-1.5 min-w-0">
                            <span className="chip h-5 px-1.5 text-[9px] uppercase tracking-wide shrink-0">
                              {meta.label}
                            </span>
                            <span className="flex items-center gap-1.5 min-w-0 text-[10px] font-mono text-text-dim">
                              <PlugZap className="w-3 h-3 shrink-0" />
                              <span className="truncate">{location}</span>
                            </span>
                          </div>
                        </div>
                        {isAdmin && (
                          <div className="flex shrink-0 items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
                            <button
                              className="btn-icon w-7 h-7 hover:!text-accent"
                              onClick={(e) => {
                                e.stopPropagation();
                                setSharingTarget(c);
                              }}
                              aria-label="Share connection"
                              title="Share connection"
                            >
                              <Share2 className="w-3.5 h-3.5" />
                            </button>
                            <button
                              className="btn-icon w-7 h-7 hover:!text-danger"
                              onClick={(e) => {
                                e.stopPropagation();
                                if (confirm(`Delete connection "${c.name}"?`)) del.mutate(c.id);
                              }}
                              aria-label="Delete connection"
                              title="Delete connection"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </div>
                        )}
                      </motion.div>
                    );
                  })}
                </div>
              </motion.section>
            ))}
          </AnimatePresence>
        </div>
      </div>

      <ConnectionSharingDialog connection={sharingTarget} onClose={() => setSharingTarget(null)} />
    </div>
  );
}

function connectionMatches(c: ConnectionSummary, query: string): boolean {
  return [
    c.name,
    c.dialect,
    DIALECT_META[c.dialect].label,
    DIALECT_META[c.dialect].kind,
    c.displayHost,
    c.displayDatabase,
    c.sharing.mode,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase()
    .includes(query);
}

function compareConnections(a: ConnectionSummary, b: ConnectionSummary, activeId: string | null) {
  if (a.id === activeId && b.id !== activeId) return -1;
  if (b.id === activeId && a.id !== activeId) return 1;
  return a.name.localeCompare(b.name, undefined, { sensitivity: 'base' });
}

function connectionLocation(c: ConnectionSummary): string {
  if (c.displayHost && c.displayDatabase) return `${c.displayHost} / ${c.displayDatabase}`;
  return c.displayHost ?? c.displayDatabase ?? 'local';
}

function SharingBadge({ sharing }: { sharing: ConnectionSummary['sharing'] }) {
  if (sharing.mode === 'private') {
    return (
      <span
        className="inline-flex items-center gap-0.5 chip text-[9px] px-1 h-4 shrink-0"
        title="Private — only the owner"
      >
        <Lock className="w-2.5 h-2.5" />
        private
      </span>
    );
  }
  if (sharing.mode === 'admins') {
    return (
      <span
        className="inline-flex items-center gap-0.5 chip text-[9px] px-1 h-4 shrink-0"
        title="Shared with every admin"
      >
        <ShieldCheck className="w-2.5 h-2.5" />
        admins
      </span>
    );
  }
  if (sharing.mode === 'all') {
    return (
      <span
        className="inline-flex items-center gap-0.5 chip text-[9px] px-1 h-4 shrink-0"
        title="Shared with everyone"
      >
        <Globe className="w-2.5 h-2.5" />
        all
      </span>
    );
  }
  return (
    <span
      className="inline-flex items-center gap-0.5 chip text-[9px] px-1 h-4 shrink-0"
      title={`Shared with ${sharing.userIds.length} user(s)`}
    >
      <UsersIcon className="w-2.5 h-2.5" />
      {sharing.userIds.length}
    </span>
  );
}
