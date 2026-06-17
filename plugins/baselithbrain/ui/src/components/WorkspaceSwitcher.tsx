import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { Check, ChevronsUpDown, Layers, Plus, Trash2 } from 'lucide-react';
import { useBrain } from '@/store';
import { cn } from '@/lib/cn';
import { popVariants } from '@/lib/motion';
import { askConfirm } from './ConfirmDialog';

/**
 * Workspace selector: switch between logical note groupings, create a new one
 * inline, or delete a non-default workspace (its notes fall back to the default,
 * never lost). Mounted in the sidebar header above the page tree.
 */
export function WorkspaceSwitcher() {
  const workspaces = useBrain((s) => s.workspaces);
  const activeWorkspace = useBrain((s) => s.activeWorkspace);
  const switchWorkspace = useBrain((s) => s.switchWorkspace);
  const createWorkspace = useBrain((s) => s.createWorkspace);
  const deleteWorkspace = useBrain((s) => s.deleteWorkspace);

  const [open, setOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState('');
  const ref = useRef<HTMLDivElement>(null);

  const active = workspaces.find((w) => w.id === activeWorkspace);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    window.addEventListener('mousedown', onClick);
    return () => window.removeEventListener('mousedown', onClick);
  }, [open]);

  const submitNew = async () => {
    const trimmed = name.trim();
    if (!trimmed) return;
    setName('');
    setCreating(false);
    setOpen(false);
    await createWorkspace(trimmed);
  };

  return (
    <div ref={ref} className="relative px-3 pb-3">
      <button
        onClick={() => setOpen((v) => !v)}
        className={cn(
          'flex w-full items-center gap-2 rounded-xl border border-[var(--color-border)]',
          'bg-[var(--color-bg)]/60 px-2.5 py-2 text-sm transition hover:border-[var(--color-border-strong)]'
        )}
      >
        <span className="bb-gradient flex size-5 shrink-0 items-center justify-center rounded-md text-white">
          <Layers className="size-3" />
        </span>
        <span className="truncate font-medium">{active?.name ?? 'My Brain'}</span>
        <span className="ml-auto text-xs text-[var(--color-faint)]">{active?.note_count ?? 0}</span>
        <ChevronsUpDown className="size-3.5 shrink-0 text-[var(--color-faint)]" />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            variants={popVariants}
            initial="hidden"
            animate="show"
            exit="exit"
            style={{ transformOrigin: 'top' }}
            className="bb-solid absolute left-3 right-3 z-30 mt-1.5 overflow-hidden rounded-xl"
          >
            <ul className="max-h-64 overflow-y-auto p-1">
              {workspaces.map((w) => (
                <li key={w.id}>
                  <div
                    onClick={() => {
                      setOpen(false);
                      void switchWorkspace(w.id);
                    }}
                    className={cn(
                      'group flex cursor-pointer items-center gap-2 rounded-lg px-2.5 py-1.5 text-sm',
                      'hover:bg-[var(--color-elevated)]'
                    )}
                  >
                    <Check
                      className={cn(
                        'size-3.5 shrink-0',
                        w.id === activeWorkspace
                          ? 'text-[var(--color-accent)] opacity-100'
                          : 'opacity-0'
                      )}
                    />
                    <span className="truncate">{w.name}</span>
                    <span className="ml-auto text-xs text-[var(--color-faint)]">
                      {w.note_count}
                    </span>
                    {w.id !== 'default' && (
                      <button
                        title="Delete workspace"
                        onClick={(e) => {
                          e.stopPropagation();
                          void askConfirm(
                            `Delete workspace “${w.name}”? Its ${w.note_count} note(s) move to My Brain.`
                          ).then((ok) => {
                            if (ok) void deleteWorkspace(w.id);
                          });
                        }}
                        className="hidden rounded p-0.5 text-[var(--color-faint)] hover:text-[var(--color-danger)] group-hover:block"
                      >
                        <Trash2 className="size-3.5" />
                      </button>
                    )}
                  </div>
                </li>
              ))}
            </ul>

            <div className="border-t border-[var(--color-border)] p-1.5">
              {creating ? (
                <input
                  autoFocus
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  onBlur={() => (name.trim() ? void submitNew() : setCreating(false))}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') void submitNew();
                    if (e.key === 'Escape') {
                      setName('');
                      setCreating(false);
                    }
                  }}
                  placeholder="Workspace name…"
                  className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] px-2 py-1.5 text-sm outline-none focus:border-[var(--color-accent)]"
                />
              ) : (
                <button
                  onClick={() => setCreating(true)}
                  className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-sm text-[var(--color-muted)] hover:bg-[var(--color-elevated)] hover:text-[var(--color-text)]"
                >
                  <Plus className="size-3.5" />
                  New workspace
                </button>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
