import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AnimatePresence, motion } from 'motion/react';
import { History, RotateCcw, X } from 'lucide-react';
import { useBrain } from '@/store';
import { api } from '@/lib/api';
import type { HistoryEntry } from '@/lib/types';
import { drawerVariants } from '@/lib/motion';

/** Version history for the active note: browse revisions, preview, restore. */
export function HistoryDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useTranslation();
  const active = useBrain((s) => s.active);
  const refreshActive = useBrain((s) => s.refreshActive);
  const [entries, setEntries] = useState<HistoryEntry[]>([]);
  const [selected, setSelected] = useState<HistoryEntry | null>(null);
  const [preview, setPreview] = useState('');

  const id = active?.id;
  const refresh = useCallback(() => {
    if (!id) return;
    api
      .history(id)
      .then(setEntries)
      .catch(() => setEntries([]));
  }, [id]);

  useEffect(() => {
    if (open) {
      setSelected(null);
      setPreview('');
      refresh();
    }
  }, [open, refresh]);

  const pick = async (entry: HistoryEntry) => {
    if (!id) return;
    setSelected(entry);
    const rev = await api.revision(id, entry.version);
    setPreview(rev.body);
  };

  const restore = async () => {
    if (!id || !selected) return;
    await api.restoreRevision(id, selected.version);
    await refreshActive(id);
    onClose();
  };

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            key="scrim"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.16 }}
            onClick={onClose}
            className="fixed inset-0 z-40 bg-[var(--color-overlay)]"
          />
          <motion.aside
            key="drawer"
            variants={drawerVariants}
            initial="hidden"
            animate="show"
            exit="exit"
            className="bb-solid fixed right-3 top-3 bottom-3 z-40 flex w-[30rem] max-w-[94vw] flex-col overflow-hidden rounded-[var(--radius-lg)]"
          >
            <header className="flex items-center gap-2 border-b border-[var(--color-border)] px-4 py-3">
              <History className="size-4 text-[var(--color-muted)]" />
              <h2 className="text-sm font-semibold">{t('history.title')}</h2>
              <button
                onClick={onClose}
                className="ml-auto rounded-lg p-1.5 text-[var(--color-muted)] hover:bg-[var(--color-elevated)]"
              >
                <X className="size-4" />
              </button>
            </header>

            <div className="flex min-h-0 flex-1">
              <div className="w-44 shrink-0 overflow-y-auto border-r border-[var(--color-border)] p-1.5">
                {entries.map((e) => (
                  <button
                    key={e.version}
                    onClick={() => void pick(e)}
                    className={
                      'block w-full rounded-lg px-2 py-1.5 text-left text-xs transition-colors ' +
                      (selected?.version === e.version
                        ? 'bg-[var(--color-accent-soft)] text-[var(--color-text)]'
                        : 'text-[var(--color-muted)] hover:bg-[var(--color-elevated)]')
                    }
                  >
                    {e.saved ? new Date(e.saved).toLocaleString() : e.version}
                  </button>
                ))}
                {!entries.length && (
                  <p className="px-2 py-6 text-center text-xs text-[var(--color-faint)]">
                    {t('history.noVersions')}
                  </p>
                )}
              </div>
              <div className="min-w-0 flex-1 overflow-y-auto p-3">
                {selected ? (
                  <pre className="whitespace-pre-wrap break-words font-mono text-xs text-[var(--color-muted)]">
                    {preview || t('history.empty')}
                  </pre>
                ) : (
                  <p className="py-8 text-center text-xs text-[var(--color-faint)]">
                    {t('history.selectVersion')}
                  </p>
                )}
              </div>
            </div>

            {selected && (
              <footer className="border-t border-[var(--color-border)] p-3">
                <button
                  onClick={() => void restore()}
                  className="bb-gradient bb-btn-glow flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium text-white"
                >
                  <RotateCcw className="size-4" />
                  {t('history.restore')}
                </button>
              </footer>
            )}
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}
