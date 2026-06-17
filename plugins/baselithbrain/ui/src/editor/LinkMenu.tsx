import { cn } from '@/lib/cn';
import { FileText, Plus } from 'lucide-react';
import type { NoteMeta } from '@/lib/types';

export interface LinkChoice {
  id: string;
  title: string;
  isNew?: boolean;
}

interface Props {
  notes: NoteMeta[];
  query: string;
  index: number;
  coords: { left: number; top: number };
  onPick: (choice: LinkChoice) => void;
}

/** Build the filtered candidate list for the `[[` autocomplete. */
export function linkChoices(notes: NoteMeta[], query: string): LinkChoice[] {
  const q = query.trim().toLowerCase();
  const matches: LinkChoice[] = notes
    .filter((n) => !q || n.title.toLowerCase().includes(q))
    .slice(0, 6)
    .map((n) => ({ id: n.id, title: n.title }));
  if (q && !notes.some((n) => n.title.toLowerCase() === q)) {
    matches.push({ id: query.trim(), title: query.trim(), isNew: true });
  }
  return matches;
}

/** Floating `[[` wikilink autocomplete, anchored at the caret. */
export function LinkMenu({ notes, query, index, coords, onPick }: Props) {
  const choices = linkChoices(notes, query);
  if (!choices.length) return null;
  return (
    <div
      className="bb-pop fixed z-50 w-72 overflow-hidden rounded-lg border border-[var(--color-border)] bg-[var(--color-elevated)] p-1 shadow-xl"
      style={{ left: coords.left, top: coords.top + 6 }}
    >
      {choices.map((c, i) => (
        <button
          key={`${c.id}-${c.isNew ? 'new' : ''}`}
          onMouseDown={(e) => {
            e.preventDefault();
            onPick(c);
          }}
          className={cn(
            'flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-left text-sm',
            i === index
              ? 'bg-[var(--color-accent-soft)] text-[var(--color-text)]'
              : 'text-[var(--color-muted)] hover:bg-[var(--color-surface)]'
          )}
        >
          {c.isNew ? (
            <Plus className="size-3.5 shrink-0" />
          ) : (
            <FileText className="size-3.5 shrink-0" />
          )}
          <span className="truncate">{c.isNew ? `Create “${c.title}”` : c.title}</span>
        </button>
      ))}
    </div>
  );
}
