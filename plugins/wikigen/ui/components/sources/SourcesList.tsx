import { Search } from 'lucide-react';
import { cn } from '../../lib/cn';
import type { Source } from '../../lib/types';
import { LABEL_BY_RANGO } from './labels';

export function SourcesList({
  sources,
  total,
  activeDocId,
  filter,
  setFilter,
  onSelect,
}: {
  sources: Source[];
  total: number;
  activeDocId: string | null;
  filter: string;
  setFilter: (v: string) => void;
  onSelect: (id: string | null, anchor?: string | null) => void;
}) {
  return (
    <div
      className={cn(
        'shrink-0 border-r border-[var(--color-border)] overflow-y-auto flex flex-col',
        'w-full sm:w-[200px] md:w-[220px]',
        activeDocId ? 'hidden sm:flex' : 'flex'
      )}
    >
      {total > 0 && (
        <div className="sticky top-0 z-10 bg-[var(--color-canvas-raised)] border-b border-[var(--color-border)] p-2">
          <div className="relative">
            <Search
              size={12}
              aria-hidden
              className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-ink-subtle"
            />
            <input
              type="search"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
              placeholder="filtra fonti…"
              aria-label="filtra elenco fonti"
              className="input-sm pl-7 pr-2 text-[11px]"
            />
          </div>
        </div>
      )}

      <div className="flex flex-col gap-1 p-2">
        {total === 0 && (
          <div className="p-3 text-[11px] leading-relaxed text-ink-subtle">
            Nessuna fonte recuperata per la conversazione corrente.
          </div>
        )}
        {total > 0 && sources.length === 0 && (
          <div className="p-3 text-[11px] leading-relaxed text-ink-subtle">
            Nessun risultato per «{filter}».
          </div>
        )}
        {sources.map((s) => (
          <button
            key={s.document_id}
            onClick={() => onSelect(activeDocId === s.document_id ? null : s.document_id, null)}
            aria-current={activeDocId === s.document_id ? 'true' : undefined}
            className={cn(
              'focus-ring rounded-lg px-2.5 py-2 text-left text-xs transition-colors',
              'hover:bg-[var(--color-surface)]',
              activeDocId === s.document_id &&
                'bg-[var(--color-surface)] ring-1 ring-[var(--color-brand-ring)]'
            )}
          >
            <div className="flex items-center gap-1 mb-0.5 flex-wrap">
              {s.rango && (
                <span className="rango-badge" data-rango={s.rango}>
                  {LABEL_BY_RANGO[s.rango] ?? s.rango}
                </span>
              )}
              {s.stato === 'superata' && (
                <span className="rango-badge bg-[var(--color-warning)]/12 text-[var(--color-warning)] border-transparent">
                  superata
                </span>
              )}
              {s.via_rinvio && (
                <span
                  className="text-[9px] text-[var(--color-accent)] font-semibold"
                  title="recuperato via rinvio incrociato"
                  aria-label="recuperato via rinvio"
                >
                  ↗
                </span>
              )}
            </div>
            <div className="font-medium text-ink line-clamp-2">{s.title}</div>
            <div className="mt-0.5 flex items-center gap-1.5 text-[10px] text-ink-subtle flex-wrap">
              {s.score != null && <span className="tabular-nums">{s.score.toFixed(2)}</span>}
              {s.edizione && <span className="tabular-nums">· Ed. {s.edizione}</span>}
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}
