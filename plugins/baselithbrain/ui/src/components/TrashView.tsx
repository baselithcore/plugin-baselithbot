import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AnimatePresence, motion } from 'motion/react';
import { Trash2, RotateCcw, X } from 'lucide-react';
import { useBrain } from '@/store';
import { api } from '@/lib/api';
import type { TrashEntry } from '@/lib/types';
import { backdropVariants, popVariants } from '@/lib/motion';
import { askConfirm } from './ConfirmDialog';

/** Recoverable soft-deleted notes: restore or permanently purge. */
export function TrashView({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useTranslation();
  const loadNotes = useBrain((s) => s.loadNotes);
  const loadTree = useBrain((s) => s.loadTree);
  const loadWorkspaces = useBrain((s) => s.loadWorkspaces);
  const [items, setItems] = useState<TrashEntry[]>([]);

  const refresh = useCallback(() => {
    api.trash().then(setItems).catch(() => setItems([]));
  }, []);

  useEffect(() => {
    if (open) refresh();
  }, [open, refresh]);

  const afterChange = async () => {
    await Promise.all([loadNotes(), loadTree(), loadWorkspaces()]);
    refresh();
  };

  const restore = async (id: string) => {
    await api.restoreTrash(id);
    await afterChange();
  };

  const purge = async (id: string, title: string) => {
    if (await askConfirm(t('trash.purgeConfirm', { title }))) {
      await api.purgeTrash(id);
      refresh();
    }
  };

  const empty = async () => {
    if (items.length && (await askConfirm(t('trash.emptyConfirm')))) {
      await api.emptyTrash();
      refresh();
    }
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          variants={backdropVariants}
          initial="hidden"
          animate="show"
          exit="exit"
          onClick={onClose}
          className="fixed inset-0 z-50 flex items-start justify-center bg-[var(--color-overlay)] pt-[12vh] backdrop-blur-sm"
        >
          <motion.div
            variants={popVariants}
            initial="hidden"
            animate="show"
            exit="exit"
            onClick={(e) => e.stopPropagation()}
            className="bb-solid w-full max-w-lg overflow-hidden rounded-xl"
          >
            <header className="flex items-center gap-2 border-b border-[var(--color-border)] px-4 py-3">
              <Trash2 className="size-4 text-[var(--color-muted)]" />
              <h2 className="text-sm font-semibold">{t('trash.title')}</h2>
              <span className="text-xs text-[var(--color-faint)]">{items.length}</span>
              <div className="ml-auto flex items-center gap-1">
                {items.length > 0 && (
                  <button
                    onClick={() => void empty()}
                    className="rounded-lg px-2 py-1 text-xs text-[var(--color-danger)] hover:bg-[var(--color-elevated)]"
                  >
                    {t('trash.empty')}
                  </button>
                )}
                <button
                  onClick={onClose}
                  className="rounded-lg p-1.5 text-[var(--color-muted)] hover:bg-[var(--color-elevated)]"
                >
                  <X className="size-4" />
                </button>
              </div>
            </header>
            <div className="max-h-[55vh] overflow-y-auto p-1.5">
              {items.map((n) => (
                <div
                  key={n.id}
                  className="group flex items-center gap-2 rounded-lg px-2.5 py-2 hover:bg-[var(--color-elevated)]"
                >
                  <span className="min-w-0 flex-1 truncate text-sm">{n.title}</span>
                  <button
                    title={t('trash.restore')}
                    onClick={() => void restore(n.id)}
                    className="rounded p-1 text-[var(--color-muted)] hover:text-[var(--color-accent)]"
                  >
                    <RotateCcw className="size-3.5" />
                  </button>
                  <button
                    title={t('trash.deleteForever')}
                    onClick={() => void purge(n.id, n.title)}
                    className="rounded p-1 text-[var(--color-faint)] hover:text-[var(--color-danger)]"
                  >
                    <Trash2 className="size-3.5" />
                  </button>
                </div>
              ))}
              {!items.length && (
                <p className="px-3 py-10 text-center text-sm text-[var(--color-faint)]">
                  {t('trash.isEmpty')}
                </p>
              )}
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
