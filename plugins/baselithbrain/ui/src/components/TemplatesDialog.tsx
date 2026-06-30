import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AnimatePresence, motion } from 'motion/react';
import { FileStack, Plus, Trash2, X } from 'lucide-react';
import { useBrain } from '@/store';
import { api } from '@/lib/api';
import type { TemplateMeta } from '@/lib/types';
import { backdropVariants, popVariants } from '@/lib/motion';
import { askConfirm } from './ConfirmDialog';

/** Client-side mirror of the backend placeholder expansion (for new notes). */
function expand(body: string, title: string): string {
  const now = new Date();
  const date = now.toISOString().slice(0, 10);
  const time = now.toTimeString().slice(0, 5);
  return body
    .replaceAll('{{date}}', date)
    .replaceAll('{{time}}', time)
    .replaceAll('{{datetime}}', `${date} ${time}`)
    .replaceAll('{{title}}', title);
}

/** Manage note templates and create new notes from them. */
export function TemplatesDialog({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useTranslation();
  const activeWorkspace = useBrain((s) => s.activeWorkspace);
  const loadNotes = useBrain((s) => s.loadNotes);
  const loadTree = useBrain((s) => s.loadTree);
  const openNote = useBrain((s) => s.openNote);
  const [items, setItems] = useState<TemplateMeta[]>([]);
  const [name, setName] = useState('');
  const [body, setBody] = useState('');

  const refresh = useCallback(() => {
    api
      .listTemplates()
      .then(setItems)
      .catch(() => setItems([]));
  }, []);

  useEffect(() => {
    if (open) refresh();
  }, [open, refresh]);

  const create = async () => {
    if (!name.trim()) return;
    await api.createTemplate({ name: name.trim(), body });
    setName('');
    setBody('');
    refresh();
  };

  const remove = async (id: string, label: string) => {
    if (await askConfirm(t('templates.deleteConfirm', { title: label }))) {
      await api.deleteTemplate(id);
      refresh();
    }
  };

  const use = async (id: string, label: string) => {
    const tpl = await api.getTemplate(id);
    const note = await api.createNote({
      title: tpl.name || label,
      body: expand(tpl.body, tpl.name || label),
      workspace: activeWorkspace,
    });
    await Promise.all([loadNotes(), loadTree()]);
    await openNote(note.id);
    onClose();
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
          className="fixed inset-0 z-50 flex items-start justify-center bg-[var(--color-overlay)] pt-[10vh] backdrop-blur-sm"
        >
          <motion.div
            variants={popVariants}
            initial="hidden"
            animate="show"
            exit="exit"
            onClick={(e) => e.stopPropagation()}
            className="bb-solid flex max-h-[78vh] w-full max-w-lg flex-col overflow-hidden rounded-xl"
          >
            <header className="flex items-center gap-2 border-b border-[var(--color-border)] px-4 py-3">
              <FileStack className="size-4 text-[var(--color-muted)]" />
              <h2 className="text-sm font-semibold">{t('templates.title')}</h2>
              <button
                onClick={onClose}
                className="ml-auto rounded-lg p-1.5 text-[var(--color-muted)] hover:bg-[var(--color-elevated)]"
              >
                <X className="size-4" />
              </button>
            </header>

            <div className="overflow-y-auto p-1.5">
              {items.map((tpl) => (
                <div
                  key={tpl.id}
                  className="group flex items-center gap-2 rounded-lg px-2.5 py-2 hover:bg-[var(--color-elevated)]"
                >
                  <span className="min-w-0 flex-1 truncate text-sm">{tpl.name}</span>
                  <button
                    onClick={() => void use(tpl.id, tpl.name)}
                    className="rounded-md px-2 py-1 text-xs text-[var(--color-accent)] hover:bg-[var(--color-accent-soft)]"
                  >
                    {t('templates.newNote')}
                  </button>
                  <button
                    title={t('common.delete')}
                    onClick={() => void remove(tpl.id, tpl.name)}
                    className="rounded p-1 text-[var(--color-faint)] hover:text-[var(--color-danger)]"
                  >
                    <Trash2 className="size-3.5" />
                  </button>
                </div>
              ))}
              {!items.length && (
                <p className="px-3 py-6 text-center text-xs text-[var(--color-faint)]">
                  {t('templates.empty')}
                </p>
              )}
            </div>

            <div className="space-y-2 border-t border-[var(--color-border)] p-3">
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={t('templates.name')}
                className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2 text-sm outline-none focus:border-[var(--color-accent)]"
              />
              <textarea
                value={body}
                onChange={(e) => setBody(e.target.value)}
                placeholder="# {{title}}&#10;&#10;Created {{date}}…"
                rows={4}
                className="w-full resize-y rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] px-3 py-2 font-mono text-xs outline-none focus:border-[var(--color-accent)]"
              />
              <button
                onClick={() => void create()}
                disabled={!name.trim()}
                className="bb-gradient bb-btn-glow flex items-center gap-1.5 rounded-lg px-3 py-2 text-sm font-medium text-white disabled:opacity-40"
              >
                <Plus className="size-4" />
                {t('templates.save')}
              </button>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
