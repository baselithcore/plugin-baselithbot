import { Download, MessagesSquare, Pen, Pin, PinOff, Trash2 } from 'lucide-react';
import { memo } from 'react';
import type { Conversation } from '../../lib/types';
import { cn } from '../../lib/cn';
import { downloadMarkdown } from '../../lib/export';

interface ConvRowProps {
  c: Conversation;
  isActive: boolean;
  isEditing: boolean;
  /** Solo passato quando isEditing=true; evita re-render row non-editanti su keystroke. */
  editingTitle?: string;
  inputRef: React.RefObject<HTMLInputElement | null>;
  setEditingTitle: (v: string) => void;
  startEdit: (c: Conversation) => void;
  commitEdit: () => void;
  cancelEdit: () => void;
  onSelect: (id: string) => void;
  onDelete?: (id: string) => void;
  onRename?: (id: string, title: string) => void;
  onTogglePin?: (id: string) => void;
}

export const ConvRow = memo(function ConvRow({
  c,
  isActive,
  isEditing,
  editingTitle,
  inputRef,
  setEditingTitle,
  startEdit,
  commitEdit,
  cancelEdit,
  onSelect,
  onDelete,
  onRename,
  onTogglePin,
}: ConvRowProps) {
  const active = isActive;
  return (
    <div
      className={cn(
        'group relative overflow-hidden rounded-lg transition-colors',
        active
          ? 'bg-white/[0.14] shadow-[inset_0_0_0_1px_rgba(255,255,255,0.09)]'
          : 'hover:bg-white/[0.08]'
      )}
    >
      {active && (
        <span
          aria-hidden
          className="absolute inset-y-1.5 left-0 w-0.5 rounded-r-full bg-white/85"
        />
      )}
      {isEditing ? (
        <div className="flex items-center gap-1.5 px-2 py-1.5">
          <MessagesSquare size={12} className="shrink-0 text-white/75" />
          <input
            ref={inputRef}
            value={editingTitle ?? ''}
            onChange={(e) => setEditingTitle(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') commitEdit();
              else if (e.key === 'Escape') cancelEdit();
            }}
            onBlur={commitEdit}
            className="focus-ring flex-1 rounded-md border border-white/20 bg-white text-sm text-[var(--color-sidebar-bg)]
                       px-1.5 py-0.5"
            aria-label="rinomina conversazione"
          />
        </div>
      ) : (
        <button
          onClick={() => onSelect(c.id)}
          onDoubleClick={() => onRename && startEdit(c)}
          className={cn(
            'focus-ring flex w-full min-w-0 items-center gap-2 rounded-lg px-2.5 py-2 text-left text-sm',
            active ? 'text-white' : 'text-white/70'
          )}
        >
          <span
            className={cn(
              'grid size-6 shrink-0 place-items-center rounded-md border',
              active
                ? 'border-white/18 bg-white/16 text-white'
                : 'border-white/8 bg-white/[0.06] text-white/48 group-hover:text-white/70'
            )}
          >
            {c.pinned ? <Pin size={11} /> : <MessagesSquare size={12} />}
          </span>
          <span className="min-w-0 flex-1 truncate pr-20 font-medium">
            {c.title || 'Senza titolo'}
          </span>
        </button>
      )}
      {!isEditing && (
        <div className="absolute right-1 top-1/2 flex -translate-y-1/2 items-center gap-0.5 rounded-md bg-[var(--color-sidebar-bg)]/85 p-0.5 opacity-0 shadow-sm backdrop-blur-sm transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
          {onTogglePin && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onTogglePin(c.id);
              }}
              className="focus-ring rounded-md p-1 text-white/45 hover:bg-white/12 hover:text-white"
              aria-label={c.pinned ? 'rimuovi fissaggio' : 'fissa in cima'}
              title={c.pinned ? 'rimuovi fissaggio' : 'fissa in cima'}
            >
              {c.pinned ? <PinOff size={11} /> : <Pin size={11} />}
            </button>
          )}
          {onRename && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                startEdit(c);
              }}
              className="focus-ring rounded-md p-1 text-white/45 hover:bg-white/12 hover:text-white"
              aria-label="rinomina"
              title="rinomina"
            >
              <Pen size={11} />
            </button>
          )}
          <button
            onClick={(e) => {
              e.stopPropagation();
              downloadMarkdown(c);
            }}
            className="focus-ring rounded-md p-1 text-white/45 hover:bg-white/12 hover:text-white"
            aria-label="esporta .md"
            title="esporta .md"
          >
            <Download size={11} />
          </button>
          {onDelete && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onDelete(c.id);
              }}
              className="focus-ring rounded-md p-1 text-white/45 hover:bg-white/12 hover:text-[var(--color-danger)]"
              aria-label="elimina"
              title="elimina"
            >
              <Trash2 size={11} />
            </button>
          )}
        </div>
      )}
    </div>
  );
});
