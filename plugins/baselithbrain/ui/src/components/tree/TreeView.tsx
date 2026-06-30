import { useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useBrain } from '@/store';
import { cn } from '@/lib/cn';
import { askConfirm } from '../ConfirmDialog';
import { TreeRow } from './TreeRow';

/**
 * Page tree: collapsible, drag-to-reparent navigation over the note hierarchy.
 * Dropping a row onto another re-parents it; dropping on the empty tail moves it
 * to the root. Self/descendant drops are rejected server-side (cycle guard).
 */
export function TreeView() {
  const { t } = useTranslation();
  const tree = useBrain((s) => s.tree);
  const activeId = useBrain((s) => s.activeId);
  const openNote = useBrain((s) => s.openNote);
  const createNote = useBrain((s) => s.createNote);
  const deleteNote = useBrain((s) => s.deleteNote);
  const moveNote = useBrain((s) => s.moveNote);

  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const [dropId, setDropId] = useState<string | null>(null);
  const [rootDrop, setRootDrop] = useState(false);
  const dragged = useRef<string | null>(null);

  const toggle = (id: string) =>
    setCollapsed((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  const drop = (targetId: string | null) => {
    const id = dragged.current;
    setDropId(null);
    setRootDrop(false);
    dragged.current = null;
    if (id && id !== targetId) void moveNote(id, targetId);
  };

  if (!tree.length) {
    return (
      <p className="px-2 py-6 text-center text-xs text-[var(--color-faint)]">{t('tree.empty')}</p>
    );
  }

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setRootDrop(true);
      }}
      onDragLeave={() => setRootDrop(false)}
      onDrop={() => drop(null)}
      className={cn('min-h-full', rootDrop && 'rounded-md ring-1 ring-[var(--color-accent)]/40')}
    >
      {tree.map((node) => (
        <TreeRow
          key={node.id}
          node={node}
          depth={0}
          activeId={activeId}
          collapsed={collapsed}
          dropId={dropId}
          onToggle={toggle}
          onOpen={(id) => void openNote(id)}
          onAddChild={(parentId) => void createNote('Untitled', parentId)}
          onDelete={(id, title) => {
            void askConfirm(t('tree.deleteConfirm', { title })).then((ok) => {
              if (ok) void deleteNote(id);
            });
          }}
          onDragStart={(id) => (dragged.current = id)}
          onDropOn={drop}
          onDragOverId={setDropId}
        />
      ))}
    </div>
  );
}
