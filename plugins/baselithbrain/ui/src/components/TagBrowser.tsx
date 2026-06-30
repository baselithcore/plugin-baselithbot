import { useEffect, useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Hash, ChevronLeft, FileText } from 'lucide-react';
import { useBrain } from '@/store';
import { api } from '@/lib/api';
import type { TagInfo } from '@/lib/types';

/** Sidebar tag index: browse all tags, drill into the notes carrying one. */
export function TagBrowser() {
  const { t } = useTranslation();
  const notes = useBrain((s) => s.notes);
  const activeWorkspace = useBrain((s) => s.activeWorkspace);
  const openNote = useBrain((s) => s.openNote);
  const [tags, setTags] = useState<TagInfo[]>([]);
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    api
      .tags(activeWorkspace)
      .then(setTags)
      .catch(() => setTags([]));
    setSelected(null);
  }, [activeWorkspace, notes.length]);

  const tagged = useMemo(() => {
    if (!selected) return [];
    const needle = selected.toLowerCase();
    return notes.filter((n) => n.tags.some((t) => t.toLowerCase() === needle));
  }, [notes, selected]);

  if (selected) {
    return (
      <div className="px-1">
        <button
          onClick={() => setSelected(null)}
          className="mb-1 flex items-center gap-1 px-1 py-1 text-xs text-[var(--color-muted)] hover:text-[var(--color-text)]"
        >
          <ChevronLeft className="size-3.5" />
          <Hash className="size-3 text-[var(--color-accent)]" />
          {selected}
        </button>
        {tagged.map((n) => (
          <button
            key={n.id}
            onClick={() => void openNote(n.id)}
            className="flex w-full items-center gap-2 rounded-lg px-2 py-1.5 text-left text-sm text-[var(--color-muted)] hover:bg-[var(--color-elevated)] hover:text-[var(--color-text)]"
          >
            <FileText className="size-3.5 shrink-0 opacity-70" />
            <span className="truncate">{n.title}</span>
          </button>
        ))}
        {!tagged.length && (
          <p className="px-2 py-6 text-center text-xs text-[var(--color-faint)]">
            {t('tags.noNotes')}
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="flex flex-wrap gap-1.5 px-1 py-1">
      {tags.map((t) => (
        <button
          key={t.tag}
          onClick={() => setSelected(t.tag)}
          className="flex items-center gap-1 rounded-full border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1 text-xs text-[var(--color-muted)] transition hover:border-[var(--color-accent)] hover:text-[var(--color-text)]"
        >
          <Hash className="size-3 text-[var(--color-accent)]" />
          {t.tag}
          <span className="text-[var(--color-faint)]">{t.count}</span>
        </button>
      ))}
      {!tags.length && (
        <p className="w-full px-2 py-6 text-center text-xs text-[var(--color-faint)]">
          {t('tags.browserEmpty')}
        </p>
      )}
    </div>
  );
}
