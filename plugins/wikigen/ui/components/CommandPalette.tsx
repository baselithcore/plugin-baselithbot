import { AnimatePresence, motion } from 'framer-motion';
import { CornerDownLeft, Search } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useEffect, useMemo, useRef, useState } from 'react';
import { useFocusTrap } from '../hooks/useFocusTrap';
import { cn } from '../lib/cn';

export interface CommandItem {
  id: string;
  label: string;
  hint?: string;
  icon?: LucideIcon;
  group: string;
  /** Voci keyword aggiuntive per match (alias nascosti) */
  keywords?: string;
  onRun: () => void;
}

interface Props {
  open: boolean;
  onClose: () => void;
  items: CommandItem[];
}

export function CommandPalette({ open, onClose, items }: Props) {
  const [query, setQuery] = useState('');
  const [cursor, setCursor] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const dialogRef = useFocusTrap<HTMLDivElement>(open);

  useEffect(() => {
    if (!open) return;
    setQuery('');
    setCursor(0);
    const t = setTimeout(() => inputRef.current?.focus(), 30);
    return () => clearTimeout(t);
  }, [open]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return items;
    return items.filter((it) => {
      const hay = [it.label, it.hint ?? '', it.group, it.keywords ?? ''].join(' ').toLowerCase();
      return hay.includes(q);
    });
  }, [items, query]);

  useEffect(() => {
    if (cursor >= filtered.length) setCursor(Math.max(0, filtered.length - 1));
  }, [filtered.length, cursor]);

  // Scroll item attivo in vista
  useEffect(() => {
    if (!open) return;
    const el = listRef.current?.querySelector<HTMLElement>(`[data-idx="${cursor}"]`);
    el?.scrollIntoView({ block: 'nearest' });
  }, [cursor, open]);

  const run = (it: CommandItem) => {
    onClose();
    // tick per lasciar chiudere il modal prima dell'azione
    setTimeout(() => it.onRun(), 0);
  };

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setCursor((c) => Math.min(c + 1, filtered.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setCursor((c) => Math.max(c - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      const it = filtered[cursor];
      if (it) run(it);
    } else if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    }
  };

  // Raggruppa per group preservando ordine di comparsa
  const grouped = useMemo(() => {
    const map = new Map<string, CommandItem[]>();
    filtered.forEach((it) => {
      if (!map.has(it.group)) map.set(it.group, []);
      map.get(it.group)!.push(it);
    });
    return Array.from(map.entries());
  }, [filtered]);

  // Indice globale (0..filtered.length-1) dato uno specifico item
  const idxOf = (it: CommandItem) => filtered.indexOf(it);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          key="palette-backdrop"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.12 }}
          onClick={onClose}
          className="fixed inset-0 z-50 grid items-start justify-items-center bg-black/40 px-4 pt-[12vh] backdrop-blur-sm"
        >
          <motion.div
            ref={dialogRef}
            key="palette"
            initial={{ opacity: 0, scale: 0.97, y: -6 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.97, y: -6 }}
            transition={{ duration: 0.14 }}
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-label="tavolozza comandi"
            className={cn(
              'w-full max-w-xl rounded-xl overflow-hidden',
              'bg-[var(--color-canvas-raised)] border border-[var(--color-border)]',
              'shadow-2xl'
            )}
          >
            <div className="flex items-center gap-2 px-3 py-2.5 border-b border-[var(--color-border)]">
              <Search size={14} className="text-ink-subtle shrink-0" />
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => {
                  setQuery(e.target.value);
                  setCursor(0);
                }}
                onKeyDown={onKeyDown}
                placeholder="cerca comandi, conversazioni…"
                className="focus-ring flex-1 bg-transparent text-sm placeholder:text-ink-subtle outline-none"
                aria-label="cerca comando"
              />
            </div>

            <div ref={listRef} className="max-h-[60vh] overflow-y-auto py-1">
              {filtered.length === 0 && (
                <div className="px-4 py-8 text-center text-[11px] text-ink-subtle italic">
                  Nessun comando per "{query}".
                </div>
              )}
              {grouped.map(([group, groupItems]) => (
                <div key={group} className="py-1">
                  <div className="px-3 py-1 text-[10px] font-semibold uppercase text-ink-subtle">
                    {group}
                  </div>
                  {groupItems.map((it) => {
                    const active = idxOf(it) === cursor;
                    const Icon = it.icon;
                    return (
                      <button
                        key={it.id}
                        data-idx={idxOf(it)}
                        onMouseMove={() => setCursor(idxOf(it))}
                        onClick={() => run(it)}
                        className={cn(
                          'w-full flex items-center gap-2.5 px-3 py-2 text-left text-sm transition-colors',
                          active
                            ? 'bg-[var(--color-surface)] text-ink'
                            : 'text-ink-muted hover:bg-[var(--color-surface)]'
                        )}
                      >
                        {Icon ? (
                          <Icon
                            size={13}
                            className={cn(
                              'shrink-0',
                              active ? 'text-[var(--color-brand)]' : 'text-ink-subtle'
                            )}
                          />
                        ) : (
                          <span className="w-[13px]" />
                        )}
                        <span className="truncate flex-1">{it.label}</span>
                        {it.hint && (
                          <span className="text-[10px] text-ink-subtle font-mono shrink-0">
                            {it.hint}
                          </span>
                        )}
                        {active && (
                          <CornerDownLeft
                            size={11}
                            className="text-[var(--color-brand)] shrink-0"
                          />
                        )}
                      </button>
                    );
                  })}
                </div>
              ))}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
