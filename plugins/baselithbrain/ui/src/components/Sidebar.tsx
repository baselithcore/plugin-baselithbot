import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { AnimatePresence, motion } from 'motion/react';
import { Plus, Brain, FileText, Trash2, Search, CalendarDays, Pin, Clock } from 'lucide-react';
import { useBrain } from '@/store';
import { cn } from '@/lib/cn';
import { itemVariants, listVariants } from '@/lib/motion';
import type { NoteMeta } from '@/lib/types';
import { askConfirm } from './ConfirmDialog';
import { Kbd, MOD } from './Kbd';
import { TreeView } from './tree/TreeView';
import { WorkspaceSwitcher } from './WorkspaceSwitcher';
import { TagBrowser } from './TagBrowser';

type View = 'notes' | 'tags';

/** Left rail: brand, quick actions, pinned/recent, the page tree (or tag browser). */
export function Sidebar() {
  const { t } = useTranslation();
  const notes = useBrain((s) => s.notes);
  const pinned = useBrain((s) => s.pinned);
  const recent = useBrain((s) => s.recent);
  const openNote = useBrain((s) => s.openNote);
  const createNote = useBrain((s) => s.createNote);
  const openDaily = useBrain((s) => s.openDaily);
  const setPalette = useBrain((s) => s.setPalette);
  const setModal = useBrain((s) => s.setModal);
  const [filter, setFilter] = useState('');
  const [view, setView] = useState<View>('notes');

  const byId = useMemo(() => new Map(notes.map((n) => [n.id, n])), [notes]);
  const q = filter.trim().toLowerCase();
  const filtered = useMemo(() => {
    if (!q) return notes;
    return notes.filter(
      (n) => n.title.toLowerCase().includes(q) || n.tags.some((t) => t.toLowerCase().includes(q))
    );
  }, [notes, q]);

  const pinnedNotes = pinned.map((id) => byId.get(id)).filter((n): n is NoteMeta => !!n);
  const recentNotes = recent
    .filter((id) => !pinned.includes(id))
    .map((id) => byId.get(id))
    .filter((n): n is NoteMeta => !!n)
    .slice(0, 6);

  return (
    <aside className="bb-glass flex h-full w-64 shrink-0 flex-col overflow-hidden rounded-[var(--radius-lg)]">
      <div className="flex items-center gap-2.5 px-4 py-4">
        <div className="bb-gradient flex size-8 items-center justify-center rounded-lg text-white">
          <Brain className="size-[1.05rem]" />
        </div>
        <span className="text-[0.95rem] font-semibold tracking-tight">BaselithBrain</span>
        <div className="ml-auto flex items-center gap-0.5">
          <button
            title={t('sidebar.today')}
            onClick={() => void openDaily()}
            className="rounded-lg p-1.5 text-[var(--color-muted)] hover:bg-[var(--color-elevated)] hover:text-[var(--color-text)]"
          >
            <CalendarDays className="size-4" />
          </button>
          <motion.button
            title={t('sidebar.newNote')}
            whileTap={{ scale: 0.92 }}
            transition={{ duration: 0.1 }}
            onClick={() => void createNote()}
            className="rounded-lg p-1.5 text-[var(--color-muted)] hover:bg-[var(--color-elevated)] hover:text-[var(--color-text)]"
          >
            <Plus className="size-4" />
          </motion.button>
        </div>
      </div>

      <WorkspaceSwitcher />

      <div className="flex gap-1 px-3 pb-2">
        {(['notes', 'tags'] as View[]).map((v) => (
          <button
            key={v}
            onClick={() => setView(v)}
            className={cn(
              'flex-1 rounded-lg px-2 py-1 text-xs font-medium capitalize transition-colors',
              view === v
                ? 'bg-[var(--color-accent-soft)] text-[var(--color-accent)]'
                : 'text-[var(--color-muted)] hover:bg-[var(--color-elevated)]'
            )}
          >
            {v === 'notes' ? t('sidebar.viewNotes') : t('sidebar.viewTags')}
          </button>
        ))}
      </div>

      {view === 'notes' && (
        <div className="px-3 pb-3">
          <div className="group relative">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-[var(--color-faint)] transition-colors group-focus-within:text-[var(--color-accent)]" />
            <input
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder={t('sidebar.filter')}
              className="w-full rounded-lg border border-[var(--color-border)] bg-[var(--color-bg)] py-2 pl-8 pr-2.5 text-sm outline-none transition placeholder:text-[var(--color-faint)] focus:border-[var(--color-accent)]"
            />
          </div>
        </div>
      )}

      <nav className="flex-1 overflow-y-auto px-2 pb-2">
        {view === 'tags' ? (
          <TagBrowser />
        ) : q ? (
          <motion.div variants={listVariants} initial="hidden" animate="show">
            <AnimatePresence>
              {filtered.map((n) => (
                <NoteRow key={n.id} note={n} onOpen={openNote} />
              ))}
            </AnimatePresence>
            {!filtered.length && (
              <p className="px-2 py-6 text-center text-xs text-[var(--color-faint)]">
                {t('sidebar.noMatch')}
              </p>
            )}
          </motion.div>
        ) : (
          <>
            {pinnedNotes.length > 0 && (
              <GroupLabel icon={<Pin className="size-3" />}>{t('sidebar.pinned')}</GroupLabel>
            )}
            {pinnedNotes.map((n) => (
              <NoteRow key={`pin-${n.id}`} note={n} onOpen={openNote} />
            ))}
            {recentNotes.length > 0 && (
              <GroupLabel icon={<Clock className="size-3" />}>{t('sidebar.recent')}</GroupLabel>
            )}
            {recentNotes.map((n) => (
              <NoteRow key={`rec-${n.id}`} note={n} onOpen={openNote} />
            ))}
            {(pinnedNotes.length > 0 || recentNotes.length > 0) && (
              <GroupLabel>{t('sidebar.allNotes')}</GroupLabel>
            )}
            <TreeView />
          </>
        )}
      </nav>

      <div className="flex items-center gap-1 border-t border-[var(--color-border)] p-2">
        <button
          onClick={() => setPalette(true)}
          className="flex flex-1 items-center gap-2 rounded-lg px-2 py-1.5 text-xs text-[var(--color-faint)] transition hover:text-[var(--color-muted)]"
        >
          <span>{t('sidebar.notesCount', { count: notes.length })}</span>
          <span className="ml-auto flex items-center gap-1">
            <Kbd keys={`${MOD}K`} /> {t('sidebar.searchHint')}
          </span>
        </button>
        <button
          title={t('sidebar.trash')}
          onClick={() => setModal('trash')}
          className="rounded-lg p-1.5 text-[var(--color-faint)] hover:bg-[var(--color-elevated)] hover:text-[var(--color-muted)]"
        >
          <Trash2 className="size-4" />
        </button>
      </div>
    </aside>
  );
}

function GroupLabel({ icon, children }: { icon?: React.ReactNode; children: React.ReactNode }) {
  return (
    <h4 className="mb-1 mt-2 flex items-center gap-1.5 px-2 text-[0.65rem] font-semibold uppercase tracking-wider text-[var(--color-faint)]">
      {icon}
      {children}
    </h4>
  );
}

function NoteRow({ note, onOpen }: { note: NoteMeta; onOpen: (id: string) => void }) {
  const { t } = useTranslation();
  const activeId = useBrain((s) => s.activeId);
  const deleteNote = useBrain((s) => s.deleteNote);
  return (
    <motion.div
      variants={itemVariants}
      layout
      onClick={() => void onOpen(note.id)}
      className={cn(
        'group flex cursor-pointer items-center gap-2 rounded-lg px-2 py-1.5 text-sm transition-colors',
        note.id === activeId
          ? 'bg-[var(--color-accent-soft)] text-[var(--color-text)]'
          : 'text-[var(--color-muted)] hover:bg-[var(--color-elevated)]'
      )}
    >
      <FileText className="size-3.5 shrink-0 opacity-70" />
      <span className="truncate">{note.title}</span>
      <button
        title={t('common.delete')}
        onClick={(e) => {
          e.stopPropagation();
          void askConfirm(t('sidebar.deleteConfirm', { title: note.title })).then(
            (ok) => ok && void deleteNote(note.id)
          );
        }}
        className="ml-auto hidden rounded p-0.5 text-[var(--color-faint)] hover:text-[var(--color-danger)] group-hover:block"
      >
        <Trash2 className="size-3.5" />
      </button>
    </motion.div>
  );
}
