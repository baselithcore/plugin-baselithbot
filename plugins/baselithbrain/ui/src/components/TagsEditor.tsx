import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AnimatePresence, motion } from 'motion/react';
import { Hash, Plus, X } from 'lucide-react';
import { useBrain } from '@/store';
import { api } from '@/lib/api';

/** Inline tag chips for the active note with an add/remove popover editor. */
export function TagsEditor() {
  const { t } = useTranslation();
  const active = useBrain((s) => s.active);
  const applyServerNote = useBrain((s) => s.applyServerNote);
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState('');
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    window.addEventListener('mousedown', onClick);
    return () => window.removeEventListener('mousedown', onClick);
  }, [open]);

  if (!active) return null;

  const commit = async (tags: string[]) => {
    const saved = await api.updateNote(active.id, { tags });
    applyServerNote(saved);
  };

  const add = () => {
    const tag = draft.trim().replace(/^#/, '');
    if (tag && !active.tags.includes(tag)) void commit([...active.tags, tag]);
    setDraft('');
  };

  const remove = (tag: string) => void commit(active.tags.filter((t) => t !== tag));

  return (
    <div ref={ref} className="relative hidden md:block">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1 rounded-full border border-[var(--color-border)] px-2 py-0.5 text-xs text-[var(--color-muted)] transition-colors hover:border-[var(--color-accent)] hover:text-[var(--color-text)]"
        title={t('tags.edit')}
      >
        <Hash className="size-3 text-[var(--color-accent)]" />
        {active.tags.length ? t('tags.count', { count: active.tags.length }) : t('tags.add')}
      </button>
      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.12 }}
            className="bb-solid absolute right-0 top-full z-50 mt-1 w-60 rounded-lg p-2"
          >
            <div className="mb-2 flex flex-wrap gap-1">
              {active.tags.map((t) => (
                <span
                  key={t}
                  className="flex items-center gap-1 rounded-full bg-[var(--color-accent-soft)] px-2 py-0.5 text-xs text-[var(--color-link)]"
                >
                  {t}
                  <button onClick={() => remove(t)} className="hover:text-[var(--color-danger)]">
                    <X className="size-3" />
                  </button>
                </span>
              ))}
              {!active.tags.length && (
                <span className="text-xs text-[var(--color-faint)]">{t('tags.none')}</span>
              )}
            </div>
            <div className="flex items-center gap-1">
              <input
                value={draft}
                onChange={(e) => setDraft(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    add();
                  }
                }}
                placeholder={t('tags.addPlaceholder')}
                className="min-w-0 flex-1 rounded-md border border-[var(--color-border)] bg-[var(--color-bg)] px-2 py-1 text-xs outline-none focus:border-[var(--color-accent)]"
              />
              <button
                onClick={add}
                className="rounded-md p-1 text-[var(--color-muted)] hover:bg-[var(--color-elevated)]"
              >
                <Plus className="size-3.5" />
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
