import { ChevronsDownUp, ChevronsUpDown, Filter, Search, X } from 'lucide-react';
import { Button, IconButton } from '../../ui';
import { Chip } from '../users/atoms';

interface Props {
  query: string;
  onQuery: (q: string) => void;
  onlyModified: boolean;
  onToggleOnlyModified: () => void;
  onExpandAll: () => void;
  onCollapseAll: () => void;
  permsCount: number;
  filteredCount: number;
  dirtyCount: number;
}

export function RolesToolbar({
  query,
  onQuery,
  onlyModified,
  onToggleOnlyModified,
  onExpandAll,
  onCollapseAll,
  permsCount,
  filteredCount,
  dirtyCount,
}: Props) {
  const hidden = permsCount - filteredCount;
  return (
    <div className="sticky top-0 z-30 flex flex-wrap items-center gap-2 border-b border-[var(--color-border)] bg-[var(--color-canvas)] px-5 py-2.5">
      <div className="relative">
        <Search
          size={12}
          className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-ink-subtle"
          aria-hidden
        />
        <input
          type="search"
          value={query}
          onChange={(e) => onQuery(e.target.value)}
          placeholder="cerca permesso o descrizione…"
          className="input-sm w-72 pl-7 pr-7"
          aria-label="cerca permesso"
        />
        {query && (
          <button
            type="button"
            onClick={() => onQuery('')}
            aria-label="azzera ricerca"
            className="absolute right-1.5 top-1/2 grid -translate-y-1/2 place-items-center rounded p-0.5 text-ink-subtle hover:text-ink"
          >
            <X size={11} />
          </button>
        )}
      </div>

      <Button
        size="sm"
        variant={onlyModified ? 'primary' : 'secondary'}
        onClick={onToggleOnlyModified}
        leadingIcon={Filter}
      >
        Solo modificati
        {dirtyCount > 0 && (
          <Chip tone={onlyModified ? 'neutral' : 'brand'} className="ml-1">
            {dirtyCount}
          </Chip>
        )}
      </Button>

      <div className="ml-auto flex items-center gap-1">
        <span className="text-[11px] text-ink-subtle">
          {filteredCount} / {permsCount} permessi
          {hidden > 0 && query && ` · ${hidden} nascosti`}
        </span>
        <IconButton
          icon={ChevronsUpDown}
          size="sm"
          aria-label="espandi tutti i gruppi"
          onClick={onExpandAll}
        />
        <IconButton
          icon={ChevronsDownUp}
          size="sm"
          aria-label="comprimi tutti i gruppi"
          onClick={onCollapseAll}
        />
      </div>
    </div>
  );
}
