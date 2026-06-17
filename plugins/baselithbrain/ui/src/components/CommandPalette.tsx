import { useEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { Search, FileText, Plus, Network, Moon, CornerDownLeft } from 'lucide-react';
import { useBrain } from '@/store';
import { api } from '@/lib/api';
import type { SearchHit } from '@/lib/types';
import { cn } from '@/lib/cn';
import { backdropVariants } from '@/lib/motion';
import { Kbd } from './Kbd';

interface Row {
  id: string;
  label: string;
  sub?: string;
  icon: React.ReactNode;
  run: () => void;
}

/** ⌘K command palette: full-text search + quick actions, keyboard-first. */
export function CommandPalette() {
  const open = useBrain((s) => s.paletteOpen);
  const setPalette = useBrain((s) => s.setPalette);
  const openNote = useBrain((s) => s.openNote);
  const createNote = useBrain((s) => s.createNote);
  const toggleGraph = useBrain((s) => s.toggleGraph);
  const toggleTheme = useBrain((s) => s.toggleTheme);
  const activeWorkspace = useBrain((s) => s.activeWorkspace);

  const [q, setQ] = useState('');
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [index, setIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      setQ('');
      setHits([]);
      setIndex(0);
      setTimeout(() => inputRef.current?.focus(), 10);
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const t = setTimeout(() => {
      if (q.trim())
        api
          .search(q, 12, activeWorkspace)
          .then(setHits)
          .catch(() => setHits([]));
      else setHits([]);
    }, 120);
    return () => clearTimeout(t);
  }, [q, open, activeWorkspace]);

  const actions: Row[] = useMemo(
    () => [
      {
        id: 'new',
        label: 'Create new note',
        icon: <Plus className="size-4" />,
        run: () => void createNote(),
      },
      {
        id: 'graph',
        label: 'Open knowledge graph',
        icon: <Network className="size-4" />,
        run: toggleGraph,
      },
      {
        id: 'theme',
        label: 'Toggle theme',
        icon: <Moon className="size-4" />,
        run: toggleTheme,
      },
    ],
    [createNote, toggleGraph, toggleTheme]
  );

  const rows: Row[] = useMemo(() => {
    const hitRows: Row[] = hits.map((h) => ({
      id: `hit-${h.id}`,
      label: h.title,
      sub: h.snippet,
      icon: <FileText className="size-4" />,
      run: () => void openNote(h.id),
    }));
    if (q.trim()) return hitRows;
    return actions;
  }, [hits, q, actions, openNote]);

  useEffect(() => setIndex(0), [rows.length]);

  const fire = (row?: Row) => {
    if (!row) return;
    row.run();
    setPalette(false);
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          variants={backdropVariants}
          initial="hidden"
          animate="show"
          exit="exit"
          className="fixed inset-0 z-50 flex items-start justify-center bg-[var(--color-overlay)] pt-[14vh] backdrop-blur-md"
          onClick={() => setPalette(false)}
        >
          <motion.div
            initial={{ opacity: 0, y: -12, scale: 0.97 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.98 }}
            transition={{ type: 'spring', stiffness: 420, damping: 30 }}
            onClick={(e) => e.stopPropagation()}
            className="bb-solid w-full max-w-xl overflow-hidden rounded-2xl shadow-2xl"
          >
            <div className="flex items-center gap-2.5 border-b border-[var(--color-border)] px-4 py-3.5">
              <Search className="size-4 text-[var(--color-accent)]" />
              <input
                ref={inputRef}
                value={q}
                onChange={(e) => setQ(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    setIndex((i) => (i + 1) % Math.max(1, rows.length));
                  } else if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    setIndex((i) => (i - 1 + rows.length) % Math.max(1, rows.length));
                  } else if (e.key === 'Enter') {
                    e.preventDefault();
                    fire(rows[index]);
                  } else if (e.key === 'Escape') {
                    setPalette(false);
                  }
                }}
                placeholder="Search notes or run a command…"
                className="flex-1 bg-transparent text-[0.95rem] outline-none placeholder:text-[var(--color-faint)]"
              />
              <Kbd keys="esc" />
            </div>
            <div className="max-h-80 overflow-y-auto p-1.5">
              {rows.map((row, i) => (
                <button
                  key={row.id}
                  onMouseEnter={() => setIndex(i)}
                  onClick={() => fire(row)}
                  className={cn(
                    'relative flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition-colors',
                    i === index
                      ? 'bg-[var(--color-accent-soft)]'
                      : 'hover:bg-[var(--color-elevated)]'
                  )}
                >
                  {i === index && (
                    <motion.span
                      layoutId="palette-cursor"
                      className="bb-gradient absolute left-0 top-1/2 h-5 w-[3px] -translate-y-1/2 rounded-full"
                      transition={{ type: 'spring', stiffness: 500, damping: 36 }}
                    />
                  )}
                  <span
                    className={cn(
                      i === index ? 'text-[var(--color-accent)]' : 'text-[var(--color-muted)]'
                    )}
                  >
                    {row.icon}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm text-[var(--color-text)]">
                      {row.label}
                    </span>
                    {row.sub && (
                      <span className="block truncate text-xs text-[var(--color-faint)]">
                        {row.sub}
                      </span>
                    )}
                  </span>
                  {i === index && <CornerDownLeft className="size-3.5 text-[var(--color-faint)]" />}
                </button>
              ))}
              {!rows.length && (
                <p className="px-3 py-8 text-center text-sm text-[var(--color-faint)]">
                  {q.trim() ? 'No results.' : 'Type to search.'}
                </p>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
