import { ChevronDown, ChevronUp, Search, X } from 'lucide-react';
import { cn } from '../../lib/cn';

export type PreviewTab = 'content' | 'verbatim';

export function PreviewToolbar({
  query,
  setQuery,
  hitCount,
  activeHit,
  onPrevHit,
  onNextHit,
  inputRef,
  verbatimCount,
  tab,
  setTab,
}: {
  query: string;
  setQuery: (v: string) => void;
  hitCount: number;
  /** 0-based index del match attivo. `-1` = nessun navigated match
   *  (utente ha appena digitato, no nav yet). */
  activeHit: number;
  onPrevHit: () => void;
  onNextHit: () => void;
  inputRef: React.RefObject<HTMLInputElement | null>;
  verbatimCount: number;
  tab: PreviewTab;
  setTab: (t: PreviewTab) => void;
}) {
  const trimmed = query.trim();
  const showCount = trimmed.length >= 2;
  const canNav = hitCount > 0;
  // 1-based display per UX (browser Cmd+F style: "3 di 7").
  const displayIndex = canNav ? (activeHit < 0 ? 1 : activeHit + 1) : 0;
  return (
    <div className="border-b border-[var(--color-border)] bg-[var(--color-canvas-raised)] px-4 py-2 space-y-2">
      <div className="relative">
        <Search
          size={12}
          aria-hidden
          className="pointer-events-none absolute left-2.5 top-1/2 -translate-y-1/2 text-ink-subtle"
        />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            // Browser Find UX: Enter → next, Shift+Enter → prev, Esc → clear.
            if (!canNav) return;
            if (e.key === 'Enter') {
              e.preventDefault();
              if (e.shiftKey) onPrevHit();
              else onNextHit();
            } else if (e.key === 'Escape' && trimmed) {
              e.preventDefault();
              setQuery('');
            }
          }}
          placeholder="cerca nel contenuto…"
          aria-label="cerca nel contenuto della fonte"
          className={cn('input-sm pl-7 text-[11.5px]', trimmed ? 'pr-32' : 'pr-2')}
        />
        {trimmed && (
          <div className="absolute right-1.5 top-1/2 -translate-y-1/2 flex items-center gap-0.5">
            {showCount ? (
              <span
                className={cn(
                  'text-[10px] tabular-nums px-1 rounded font-medium',
                  hitCount > 0 ? 'text-[var(--color-brand)]' : 'text-ink-subtle'
                )}
                aria-live="polite"
                title={hitCount === 0 ? 'nessun match' : `${displayIndex} di ${hitCount}`}
              >
                {canNav ? `${displayIndex}/${hitCount}` : '0'}
              </span>
            ) : (
              <span
                className="text-[9px] uppercase tracking-wide text-ink-subtle"
                title="digita almeno 2 caratteri per ricercare"
              >
                min 2
              </span>
            )}
            {canNav && (
              <>
                <button
                  type="button"
                  onClick={onPrevHit}
                  aria-label="match precedente (Shift+Enter)"
                  title="precedente — Shift+Enter"
                  className="focus-ring inline-flex size-5 items-center justify-center rounded-md
                             text-ink-subtle hover:bg-[var(--color-surface)] hover:text-ink"
                >
                  <ChevronUp size={11} aria-hidden />
                </button>
                <button
                  type="button"
                  onClick={onNextHit}
                  aria-label="match successivo (Enter)"
                  title="successivo — Enter"
                  className="focus-ring inline-flex size-5 items-center justify-center rounded-md
                             text-ink-subtle hover:bg-[var(--color-surface)] hover:text-ink"
                >
                  <ChevronDown size={11} aria-hidden />
                </button>
              </>
            )}
            <button
              type="button"
              onClick={() => setQuery('')}
              aria-label="cancella ricerca"
              className="focus-ring inline-flex size-5 items-center justify-center rounded-md
                         text-ink-subtle hover:bg-[var(--color-surface)] hover:text-ink"
            >
              <X size={10} aria-hidden />
            </button>
          </div>
        )}
      </div>

      {verbatimCount > 0 && (
        <div
          role="tablist"
          aria-label="modalità anteprima"
          className="inline-flex rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] p-0.5 text-[10.5px] font-medium"
        >
          <TabButton
            active={tab === 'content'}
            onClick={() => setTab('content')}
            label="Contenuto"
          />
          <TabButton
            active={tab === 'verbatim'}
            onClick={() => setTab('verbatim')}
            label={`Verbatim (${verbatimCount})`}
          />
        </div>
      )}
    </div>
  );
}

function TabButton({
  active,
  onClick,
  label,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
}) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={cn(
        'focus-ring rounded px-2 py-1 transition-colors',
        active
          ? 'bg-[var(--color-canvas-raised)] text-ink shadow-xs'
          : 'text-ink-subtle hover:text-ink'
      )}
    >
      {label}
    </button>
  );
}
