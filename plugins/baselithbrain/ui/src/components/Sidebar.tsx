import { useMemo, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { Plus, Brain, FileText, Trash2, Search } from 'lucide-react';
import { useBrain } from '@/store';
import { cn } from '@/lib/cn';
import { itemVariants, listVariants } from '@/lib/motion';
import { askConfirm } from './ConfirmDialog';
import { Kbd, MOD } from './Kbd';
import { TreeView } from './tree/TreeView';
import { WorkspaceSwitcher } from './WorkspaceSwitcher';

/** Left rail: brand, new-note, quick filter, and the page tree. */
export function Sidebar() {
  const notes = useBrain((s) => s.notes);
  const activeId = useBrain((s) => s.activeId);
  const openNote = useBrain((s) => s.openNote);
  const createNote = useBrain((s) => s.createNote);
  const deleteNote = useBrain((s) => s.deleteNote);
  const setPalette = useBrain((s) => s.setPalette);
  const [filter, setFilter] = useState('');

  const q = filter.trim().toLowerCase();
  const filtered = useMemo(() => {
    if (!q) return notes;
    return notes.filter(
      (n) => n.title.toLowerCase().includes(q) || n.tags.some((t) => t.toLowerCase().includes(q))
    );
  }, [notes, q]);

  return (
    <aside className="bb-glass flex h-full w-64 shrink-0 flex-col overflow-hidden rounded-[var(--radius-lg)]">
      <div className="flex items-center gap-2.5 px-4 py-4">
        <div className="bb-gradient bb-btn-glow flex size-8 items-center justify-center rounded-xl text-white">
          <Brain className="size-[1.05rem]" />
        </div>
        <span className="bb-gradient-text text-[0.95rem] font-bold tracking-tight">
          BaselithBrain
        </span>
        <motion.button
          title="New note"
          whileTap={{ scale: 0.88 }}
          whileHover={{ rotate: 90 }}
          transition={{ type: 'spring', stiffness: 400, damping: 18 }}
          onClick={() => void createNote()}
          className="ml-auto rounded-lg p-1.5 text-[var(--color-muted)] hover:bg-[var(--color-elevated)] hover:text-[var(--color-text)]"
        >
          <Plus className="size-4" />
        </motion.button>
      </div>

      <WorkspaceSwitcher />

      <div className="px-3 pb-3">
        <div className="group relative">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-[var(--color-faint)] transition-colors group-focus-within:text-[var(--color-accent)]" />
          <input
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            placeholder="Filter notes…"
            className="w-full rounded-xl border border-[var(--color-border)] bg-[var(--color-bg)]/60 py-2 pl-8 pr-2.5 text-sm outline-none transition placeholder:text-[var(--color-faint)] focus:border-[var(--color-accent)] focus:shadow-[0_0_0_3px_var(--color-accent-soft)]"
          />
        </div>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 pb-2">
        {q ? (
          <motion.div variants={listVariants} initial="hidden" animate="show">
            <AnimatePresence>
              {filtered.map((n) => (
                <motion.div
                  key={n.id}
                  variants={itemVariants}
                  layout
                  onClick={() => void openNote(n.id)}
                  className={cn(
                    'group flex cursor-pointer items-center gap-2 rounded-lg px-2 py-1.5 text-sm transition-colors',
                    n.id === activeId
                      ? 'bg-[var(--color-accent-soft)] text-[var(--color-text)]'
                      : 'text-[var(--color-muted)] hover:bg-[var(--color-elevated)]/70'
                  )}
                >
                  <FileText className="size-3.5 shrink-0 opacity-70" />
                  <span className="truncate">{n.title}</span>
                  <button
                    title="Delete"
                    onClick={(e) => {
                      e.stopPropagation();
                      void askConfirm(`Delete “${n.title}”?`).then((ok) => {
                        if (ok) void deleteNote(n.id);
                      });
                    }}
                    className="ml-auto hidden rounded p-0.5 text-[var(--color-faint)] hover:text-[var(--color-danger)] group-hover:block"
                  >
                    <Trash2 className="size-3.5" />
                  </button>
                </motion.div>
              ))}
            </AnimatePresence>
            {!filtered.length && (
              <p className="px-2 py-6 text-center text-xs text-[var(--color-faint)]">
                No notes match.
              </p>
            )}
          </motion.div>
        ) : (
          <TreeView />
        )}
      </nav>

      <button
        onClick={() => setPalette(true)}
        className="m-2 flex items-center gap-2 rounded-xl border border-[var(--color-border)] px-3 py-2 text-xs text-[var(--color-faint)] transition hover:border-[var(--color-border-strong)] hover:text-[var(--color-muted)]"
      >
        <span>{notes.length} notes</span>
        <span className="ml-auto flex items-center gap-1">
          <Kbd keys={`${MOD}K`} /> search
        </span>
      </button>
    </aside>
  );
}
