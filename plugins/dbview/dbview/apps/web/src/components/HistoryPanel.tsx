import { useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { AnimatePresence, motion } from 'framer-motion';
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  Copy,
  Database,
  History,
  Loader2,
  Search,
  Star,
  Trash2,
  X,
} from 'lucide-react';
import { toast } from 'sonner';
import type { HistoryEntry } from '@dbview/shared';
import { api } from '../lib/api.js';
import { useAppStore } from '../store/app.js';
import { cn } from '../lib/cn.js';

const HISTORY_QUERY_KEY = ['history'] as const;

export function HistoryPanel() {
  const open = useAppStore((s) => s.historyOpen);
  const setOpen = useAppStore((s) => s.setHistoryOpen);
  const activeConnId = useAppStore((s) => s.activeConnectionId);

  const [scope, setScope] = useState<'all' | 'connection'>('all');
  const [favoritesOnly, setFavoritesOnly] = useState(false);
  const [search, setSearch] = useState('');

  useEffect(() => {
    if (!open) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false);
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [open, setOpen]);

  const qc = useQueryClient();
  const list = useQuery({
    queryKey: [...HISTORY_QUERY_KEY, scope === 'connection' ? activeConnId : null, favoritesOnly],
    queryFn: () =>
      api.listHistory({
        connectionId: scope === 'connection' && activeConnId ? activeConnId : undefined,
        favoritesOnly: favoritesOnly || undefined,
        limit: 200,
        offset: 0,
      }),
    enabled: open,
  });

  const filtered = useMemo<HistoryEntry[]>(() => {
    if (!list.data) return [];
    const q = search.trim().toLowerCase();
    if (!q) return list.data.entries;
    return list.data.entries.filter(
      (e) =>
        e.prompt.toLowerCase().includes(q) ||
        e.query.toLowerCase().includes(q) ||
        e.connectionName.toLowerCase().includes(q),
    );
  }, [list.data, search]);

  const toggleFav = useMutation({
    mutationFn: ({ id, favorite }: { id: string; favorite: boolean }) =>
      api.toggleFavorite(id, favorite),
    onSuccess: () => qc.invalidateQueries({ queryKey: HISTORY_QUERY_KEY }),
    onError: (err: Error) => toast.error('Failed to toggle favorite', { description: err.message }),
  });

  const remove = useMutation({
    mutationFn: (id: string) => api.deleteHistory(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: HISTORY_QUERY_KEY }),
    onError: (err: Error) => toast.error('Delete failed', { description: err.message }),
  });

  const clearAll = useMutation({
    mutationFn: () =>
      api.clearHistory(scope === 'connection' && activeConnId ? activeConnId : undefined),
    onSuccess: (data) => {
      toast.success(`Cleared ${data.removed} entries`);
      qc.invalidateQueries({ queryKey: HISTORY_QUERY_KEY });
    },
    onError: (err: Error) => toast.error('Clear failed', { description: err.message }),
  });

  if (typeof document === 'undefined') return null;

  return createPortal(
    <>
      {open && (
        <div
          onClick={() => setOpen(false)}
          className="fixed inset-0 z-40 bg-black/30 backdrop-blur-[2px] animate-fade-in"
          aria-hidden
        />
      )}
      <AnimatePresence>
        {open && (
          <motion.aside
            key="history-panel"
            role="dialog"
            aria-modal="false"
            aria-label="Query history"
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
            className="fixed top-0 right-0 z-50 h-full w-[560px] max-w-[95vw] flex flex-col border-l shadow-2xl pointer-events-auto"
            style={{
              background:
                'linear-gradient(180deg, rgb(var(--surface-elevated)), rgb(var(--surface-1)))',
              borderColor: 'rgb(var(--border-subtle))',
            }}
          >
            <Header
              total={list.data?.total ?? 0}
              shown={filtered.length}
              onClose={() => setOpen(false)}
              onClear={() => {
                if (window.confirm('Remove all non-favorite history entries?')) clearAll.mutate();
              }}
              clearing={clearAll.isPending}
            />

            <Controls
              scope={scope}
              setScope={setScope}
              favoritesOnly={favoritesOnly}
              setFavoritesOnly={setFavoritesOnly}
              search={search}
              setSearch={setSearch}
              hasConnection={!!activeConnId}
            />

            <div className="flex-1 min-h-0 overflow-auto p-2 flex flex-col gap-1.5">
              {list.isLoading && (
                <div className="flex items-center justify-center p-8 text-text-muted text-[12px] gap-2">
                  <Loader2 className="w-4 h-4 animate-spin" />
                  loading…
                </div>
              )}
              {list.error && (
                <div className="p-4 text-[12px] text-danger">{(list.error as Error).message}</div>
              )}
              {list.data && filtered.length === 0 && (
                <div className="text-[12px] text-text-dim italic px-3 py-6 text-center">
                  No entries match.
                </div>
              )}
              {filtered.map((e) => (
                <Row
                  key={e.id}
                  entry={e}
                  onToggleFav={() => toggleFav.mutate({ id: e.id, favorite: !e.favorite })}
                  onDelete={() => remove.mutate(e.id)}
                  onCopy={() => {
                    navigator.clipboard.writeText(e.query);
                    toast.success('Query copied');
                  }}
                />
              ))}
            </div>
          </motion.aside>
        )}
      </AnimatePresence>
    </>,
    document.body,
  );
}

interface HeaderProps {
  total: number;
  shown: number;
  onClose: () => void;
  onClear: () => void;
  clearing: boolean;
}

function Header({ total, shown, onClose, onClear, clearing }: HeaderProps) {
  return (
    <div
      className="flex items-center justify-between gap-3 px-4 h-12 border-b shrink-0"
      style={{ borderColor: 'rgb(var(--border-subtle))' }}
    >
      <div className="flex items-center gap-2 min-w-0">
        <History className="w-3.5 h-3.5 text-accent shrink-0" />
        <div className="flex flex-col leading-tight min-w-0">
          <div className="text-[13px] font-semibold truncate">Query history</div>
          <div className="text-[10px] font-mono text-text-dim truncate">
            {shown} shown · {total} stored
          </div>
        </div>
      </div>
      <div className="flex items-center gap-1 shrink-0">
        <button
          onClick={onClear}
          className="btn-icon"
          title="Clear non-favorite entries"
          disabled={clearing}
        >
          {clearing ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Trash2 className="w-3.5 h-3.5" />
          )}
        </button>
        <button onClick={onClose} className="btn-icon" aria-label="Close">
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
}

interface ControlsProps {
  scope: 'all' | 'connection';
  setScope: (s: 'all' | 'connection') => void;
  favoritesOnly: boolean;
  setFavoritesOnly: (v: boolean) => void;
  search: string;
  setSearch: (v: string) => void;
  hasConnection: boolean;
}

function Controls({
  scope,
  setScope,
  favoritesOnly,
  setFavoritesOnly,
  search,
  setSearch,
  hasConnection,
}: ControlsProps) {
  return (
    <div
      className="flex flex-col gap-2 px-3 py-2 border-b shrink-0"
      style={{ borderColor: 'rgb(var(--border-subtle))' }}
    >
      <div
        className="flex items-center gap-2 px-2 h-8 rounded-md text-[12px]"
        style={{
          background: 'rgb(var(--surface-2) / 0.6)',
          border: '1px solid rgb(var(--border-subtle))',
        }}
      >
        <Search className="w-3.5 h-3.5 text-text-dim" />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Filter prompts, queries, connections…"
          className="bg-transparent flex-1 outline-none placeholder:text-text-dim"
        />
      </div>
      <div className="flex items-center gap-2">
        <div className="segmented h-7">
          <button
            className={cn(
              'segmented-item font-mono text-[10px]',
              scope === 'all' && 'segmented-item-active',
            )}
            onClick={() => setScope('all')}
          >
            All
          </button>
          <button
            className={cn(
              'segmented-item font-mono text-[10px]',
              scope === 'connection' && 'segmented-item-active',
            )}
            onClick={() => setScope('connection')}
            disabled={!hasConnection}
            title={hasConnection ? 'Filter to active connection' : 'Pick a connection first'}
          >
            Active conn
          </button>
        </div>
        <button
          className={cn(
            'h-7 px-2 inline-flex items-center gap-1.5 rounded-md text-[10px] font-mono border transition-colors',
            favoritesOnly ? 'text-accent' : 'text-text-muted',
          )}
          style={{
            background: favoritesOnly ? 'rgb(var(--accent) / 0.12)' : 'rgb(var(--surface-2) / 0.6)',
            borderColor: favoritesOnly ? 'rgb(var(--accent) / 0.45)' : 'rgb(var(--border-subtle))',
          }}
          onClick={() => setFavoritesOnly(!favoritesOnly)}
          aria-pressed={favoritesOnly}
        >
          <Star className={cn('w-3 h-3', favoritesOnly && 'fill-current')} />
          Favorites
        </button>
      </div>
    </div>
  );
}

interface RowProps {
  entry: HistoryEntry;
  onToggleFav: () => void;
  onDelete: () => void;
  onCopy: () => void;
}

function Row({ entry, onToggleFav, onDelete, onCopy }: RowProps) {
  const created = new Date(entry.createdAt);
  return (
    <div
      className="rounded-md p-2.5 flex flex-col gap-1.5 group transition-colors hover:ring-1 hover:ring-accent/30"
      style={{
        background: 'rgb(var(--surface-2) / 0.5)',
        border: '1px solid rgb(var(--border-subtle))',
      }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="text-[12.5px] font-medium leading-snug flex-1 min-w-0 break-words">
          {entry.prompt}
        </div>
        <div className="flex items-center gap-0.5 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={onToggleFav}
            className="btn-icon w-6 h-6"
            title={entry.favorite ? 'Remove from favorites' : 'Add to favorites'}
            aria-pressed={entry.favorite}
          >
            <Star
              className={cn('w-3.5 h-3.5', entry.favorite && 'fill-amber-400 text-amber-400')}
            />
          </button>
          <button onClick={onCopy} className="btn-icon w-6 h-6" title="Copy query">
            <Copy className="w-3.5 h-3.5" />
          </button>
          <button onClick={onDelete} className="btn-icon w-6 h-6" title="Delete entry">
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
        {entry.favorite && (
          <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400 group-hover:hidden" />
        )}
      </div>
      <code
        className="text-[10.5px] font-mono px-2 py-1 rounded block whitespace-pre-wrap break-all"
        style={{
          background: 'rgb(var(--surface-3) / 0.7)',
          color: 'rgb(var(--text-muted))',
        }}
      >
        {entry.query.length > 220 ? entry.query.slice(0, 217) + '…' : entry.query}
      </code>
      <div className="flex items-center gap-2 text-[10px] font-mono text-text-dim flex-wrap">
        {entry.ok ? (
          <CheckCircle2 className="w-3 h-3 text-success" />
        ) : (
          <AlertCircle className="w-3 h-3 text-danger" />
        )}
        <span className="flex items-center gap-1">
          <Database className="w-3 h-3" />
          {entry.connectionName}
        </span>
        <span>
          {entry.provider}/{entry.model}
        </span>
        {entry.rowCount !== null && <span>{entry.rowCount} rows</span>}
        {entry.durationMs !== null && (
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {entry.durationMs}ms
          </span>
        )}
        <span className="ml-auto" title={created.toISOString()}>
          {formatRelative(created)}
        </span>
      </div>
      {!entry.ok && entry.errorMessage && (
        <div className="text-[10px] text-danger leading-snug break-words">
          {entry.errorCode ? `[${entry.errorCode}] ` : ''}
          {entry.errorMessage}
        </div>
      )}
    </div>
  );
}

function formatRelative(d: Date): string {
  const diff = Date.now() - d.getTime();
  const sec = Math.floor(diff / 1000);
  if (sec < 60) return `${sec}s ago`;
  const min = Math.floor(sec / 60);
  if (min < 60) return `${min}m ago`;
  const hr = Math.floor(min / 60);
  if (hr < 24) return `${hr}h ago`;
  const day = Math.floor(hr / 24);
  if (day < 30) return `${day}d ago`;
  return d.toISOString().slice(0, 10);
}
