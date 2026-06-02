import { ChevronDown, ExternalLink, FileText } from 'lucide-react';
import { useState } from 'react';
import type { Citation } from '../../lib/citations';
import { cn } from '../../lib/cn';
import type { Message as Msg } from '../../lib/types';
import { labelForRango } from '../sources/labels';

const EXTRAS_COLLAPSED_LIMIT = 4;

/**
 * Blocco "Fonti" in fondo al messaggio.
 * - Citazioni numerate coerenti con i badge inline [n]
 * - Sources extra (recuperate ma non citate inline) elencate a parte
 * - Riga citation interamente cliccabile → drawer al punto giusto
 * - Extras > soglia collassati di default per ridurre rumore visivo
 */
export function SourcesFooter({
  citations,
  extras,
  onOpenSources,
  onPickSource,
}: {
  citations: Citation[];
  extras: Msg['sources'];
  onOpenSources: () => void;
  onPickSource: (docId: string, anchor?: string) => void;
}) {
  const cited = citations.filter((c) => c.source !== null);
  const [extrasOpen, setExtrasOpen] = useState(false);
  if (cited.length === 0 && (!extras || extras.length === 0)) return null;

  const showExtrasToggle = (extras?.length ?? 0) > EXTRAS_COLLAPSED_LIMIT;
  const visibleExtras = extras
    ? showExtrasToggle && !extrasOpen
      ? extras.slice(0, EXTRAS_COLLAPSED_LIMIT)
      : extras
    : [];

  const handlePick = (docId: string, anchor?: string) => {
    onPickSource(docId, anchor);
    onOpenSources();
  };

  return (
    <div
      className="mt-4 rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)]/60 p-2.5"
      aria-label="fonti citate"
    >
      <div className="mb-2 flex items-center justify-between px-0.5">
        <span className="text-[10px] font-semibold uppercase tracking-wide text-ink-subtle">
          {cited.length > 0 ? `Fonti citate (${cited.length})` : 'Fonti consultate'}
        </span>
        <button
          onClick={onOpenSources}
          className="focus-ring inline-flex items-center gap-1 rounded text-[10px] font-medium text-ink-muted hover:text-ink"
        >
          Apri pannello <ExternalLink size={9} aria-hidden />
        </button>
      </div>

      {cited.length > 0 && (
        <ol className="flex flex-col gap-1">
          {cited.map((c) => (
            <li key={c.n}>
              <button
                onClick={() => handlePick(c.source!.document_id, c.anchor)}
                className="focus-ring group/src flex w-full items-start gap-2 rounded-md
                           px-1.5 py-1 text-left transition-colors
                           hover:bg-[var(--color-canvas-raised)]"
                title="apri nel pannello fonti"
              >
                <span className="citation-ref shrink-0 !cursor-default hover:!bg-[var(--color-brand-soft)] hover:!text-[var(--color-brand)] hover:!translate-y-0">
                  {c.n}
                </span>
                <span className="min-w-0 flex-1">
                  <span className="flex items-center gap-1.5 flex-wrap">
                    <span className="text-xs font-medium text-ink group-hover/src:text-[var(--color-brand)] transition-colors truncate">
                      {c.source!.title}
                    </span>
                    {c.source!.rango && (
                      <span className="rango-badge" data-rango={c.source!.rango}>
                        {labelForRango(c.source!.rango)}
                      </span>
                    )}
                    {c.source!.edizione && (
                      <span className="text-[10px] text-ink-subtle tabular-nums">
                        Ed. {c.source!.edizione}
                      </span>
                    )}
                    {c.anchor && (
                      <span className="text-[10px] font-mono text-ink-subtle">#{c.anchor}</span>
                    )}
                  </span>
                </span>
                <span
                  className="shrink-0 inline-flex items-center gap-1 rounded-md
                             border border-[var(--color-border)] bg-[var(--color-canvas-raised)] px-1.5 py-0.5
                             text-[10px] text-ink-muted opacity-0 group-hover/src:opacity-100
                             group-focus-visible/src:opacity-100 transition-opacity"
                  aria-hidden
                >
                  <ExternalLink size={9} /> verifica
                </span>
              </button>
            </li>
          ))}
        </ol>
      )}

      {extras && extras.length > 0 && (
        <>
          <div className="mt-2 mb-1 flex items-center justify-between px-0.5">
            <span className="text-[10px] font-semibold uppercase tracking-wide text-ink-subtle">
              Anche consultate ({extras.length})
            </span>
            {showExtrasToggle && (
              <button
                type="button"
                onClick={() => setExtrasOpen((v) => !v)}
                aria-expanded={extrasOpen}
                className="focus-ring inline-flex items-center gap-1 rounded text-[10px] font-medium text-ink-muted hover:text-ink"
              >
                {extrasOpen ? 'mostra meno' : `mostra tutte (${extras.length})`}
                <ChevronDown
                  size={10}
                  aria-hidden
                  className={cn('transition-transform', extrasOpen && 'rotate-180')}
                />
              </button>
            )}
          </div>
          <div className="flex flex-wrap gap-1.5 px-0.5">
            {visibleExtras.map((s) => (
              <button
                key={s.document_id}
                onClick={() => handlePick(s.document_id)}
                className="chip transition-colors focus-ring hover:bg-[var(--color-surface-hover)] hover:text-ink"
                title={s.title}
              >
                <FileText size={10} className="text-[var(--color-brand)]" aria-hidden />
                <span className="max-w-[180px] truncate">{s.title}</span>
                {s.via_rinvio && (
                  <span
                    className="text-[9px] text-[var(--color-accent)]"
                    title="recuperato tramite collegamento"
                    aria-label="via rinvio"
                  >
                    ↗
                  </span>
                )}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
