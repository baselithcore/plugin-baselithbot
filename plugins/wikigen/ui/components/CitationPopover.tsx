import { AnimatePresence, motion } from 'framer-motion';
import { ArrowUpRight, ExternalLink, Loader2 } from 'lucide-react';
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Citation } from '../lib/citations';
import { buildExcerpt } from '../lib/excerpt';
import { duration, ease } from '../lib/motion';
import { getCachedPage, loadPage } from '../lib/pageCache';

interface Props {
  citation: Citation;
  anchorEl: HTMLElement | null;
  open: boolean;
  onOpenSource: () => void;
  onClose: () => void;
}

interface PageData {
  title: string;
  body: string;
  obsidianUri: string | null;
}

interface Position {
  top: number;
  left: number;
  placement: 'top' | 'bottom';
}

const POPOVER_W = 380;
const POPOVER_MAX_H = 280;

/**
 * Popover stile NotebookLM: hover/focus su [n] mostra titolo + excerpt
 * dal punto citato, con bottone "Apri" per il drawer completo. Posizione
 * calcolata via getBoundingClientRect (no lib esterna), si adatta sopra
 * o sotto al chip in base allo spazio disponibile.
 */
export function CitationPopover({ citation, anchorEl, open, onOpenSource, onClose }: Props) {
  const popRef = useRef<HTMLDivElement>(null);
  const [page, setPage] = useState<PageData | null>(() => {
    const docId = citation.source?.document_id;
    if (!docId) return null;
    const hit = getCachedPage(docId);
    return hit ? { title: hit.title, body: hit.body, obsidianUri: hit.obsidian_uri ?? null } : null;
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pos, setPos] = useState<Position | null>(null);

  // Lazy fetch al primo open quando non in cache
  useEffect(() => {
    if (!open) return;
    const docId = citation.source?.document_id;
    if (!docId) return;
    if (page) return;
    const ctrl = new AbortController();
    setLoading(true);
    setError(null);
    loadPage(docId, ctrl.signal)
      .then((p) => setPage({ title: p.title, body: p.body, obsidianUri: p.obsidian_uri ?? null }))
      .catch((e: Error) => {
        if (e.name !== 'AbortError') setError('Anteprima non disponibile.');
      })
      .finally(() => setLoading(false));
    return () => ctrl.abort();
  }, [open, citation.source?.document_id, page]);

  // Posizionamento — sopra/sotto in base allo spazio
  useLayoutEffect(() => {
    if (!open || !anchorEl) {
      setPos(null);
      return;
    }
    const update = () => {
      const rect = anchorEl.getBoundingClientRect();
      const vw = window.innerWidth;
      const vh = window.innerHeight;
      const spaceBelow = vh - rect.bottom;
      const spaceAbove = rect.top;
      const placement: 'top' | 'bottom' =
        spaceBelow >= POPOVER_MAX_H + 12 || spaceBelow >= spaceAbove ? 'bottom' : 'top';
      const top =
        placement === 'bottom' ? rect.bottom + 8 : Math.max(8, rect.top - POPOVER_MAX_H - 8);
      const desiredLeft = rect.left + rect.width / 2 - POPOVER_W / 2;
      const left = Math.max(8, Math.min(desiredLeft, vw - POPOVER_W - 8));
      setPos({ top, left, placement });
    };
    update();
    window.addEventListener('scroll', update, true);
    window.addEventListener('resize', update);
    return () => {
      window.removeEventListener('scroll', update, true);
      window.removeEventListener('resize', update);
    };
  }, [open, anchorEl]);

  // ESC chiude
  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  const excerpt = page ? buildExcerpt(page.body, citation.anchor) : null;
  const source = citation.source;

  return (
    <AnimatePresence>
      {open && pos && source && (
        <motion.div
          ref={popRef}
          role="dialog"
          aria-modal="false"
          aria-label={`anteprima fonte ${citation.n}`}
          initial={{ opacity: 0, y: pos.placement === 'bottom' ? -4 : 4 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: pos.placement === 'bottom' ? -4 : 4 }}
          transition={{ duration: duration.fast, ease: ease.outQuart }}
          style={{
            position: 'fixed',
            top: pos.top,
            left: pos.left,
            width: POPOVER_W,
            maxHeight: POPOVER_MAX_H,
            zIndex: 60,
          }}
          className="rounded-lg border border-[var(--color-border)] bg-[var(--color-canvas-raised)]
                     shadow-lg overflow-hidden flex flex-col"
          onMouseEnter={(e) => e.stopPropagation()}
        >
          <div className="px-3 py-2 border-b border-[var(--color-border)] bg-[var(--color-surface)]">
            <div className="flex items-start justify-between gap-2">
              <div className="min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="citation-ref !cursor-default !translate-y-0">{citation.n}</span>
                  <span className="text-[11px] font-semibold text-ink truncate">
                    {page?.title ?? source.title}
                  </span>
                </div>
                <div className="mt-0.5 text-[10px] font-mono text-ink-subtle truncate">
                  {source.document_id}
                  {citation.anchor && (
                    <span className="ml-1 text-[var(--color-brand)]">#{citation.anchor}</span>
                  )}
                </div>
              </div>
              <button
                type="button"
                onClick={onOpenSource}
                className="focus-ring shrink-0 inline-flex items-center gap-1 rounded-md
                           border border-[var(--color-border)] bg-[var(--color-canvas-raised)]
                           px-2 py-1 text-[10px] font-medium text-ink-muted hover:text-[var(--color-brand)]
                           hover:border-[var(--color-brand-ring)]"
                title="apri nel pannello fonti"
              >
                Apri <ArrowUpRight size={10} />
              </button>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto px-3 py-2 text-[12px] leading-relaxed text-ink">
            {loading && !excerpt && (
              <div className="flex items-center gap-2 text-ink-subtle text-[11px]">
                <Loader2 size={12} className="animate-spin" /> caricamento anteprima…
              </div>
            )}
            {error && !excerpt && (
              <div className="text-[11px] text-[var(--color-danger)]">{error}</div>
            )}
            {excerpt && (
              <ExcerptText
                text={excerpt.text}
                match={excerpt.match}
                truncatedStart={excerpt.truncatedStart}
                truncatedEnd={excerpt.truncatedEnd}
              />
            )}
          </div>

          {page?.obsidianUri && (
            <div className="px-3 py-1.5 border-t border-[var(--color-border)] bg-[var(--color-surface)]/60">
              <a
                href={page.obsidianUri}
                onClick={() => {
                  void import('../lib/onboarding').then((m) => m.dismiss('obsidian.first_open'));
                }}
                className="focus-ring inline-flex items-center gap-1 text-[10px]
                           font-medium text-ink-muted hover:text-ink"
                title="Apri questa pagina nel tuo vault Obsidian (preview-mode)"
              >
                Apri in Obsidian <ExternalLink size={9} />
              </a>
            </div>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function ExcerptText({
  text,
  truncatedStart,
  truncatedEnd,
}: {
  text: string;
  match: string | null;
  truncatedStart: boolean;
  truncatedEnd: boolean;
}) {
  const md = useMemo(() => {
    const prefix = truncatedStart ? '… ' : '';
    const suffix = truncatedEnd ? ' …' : '';
    return prefix + text + suffix;
  }, [text, truncatedStart, truncatedEnd]);
  return (
    <div className="md md--preview text-[12px] leading-relaxed">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{md}</ReactMarkdown>
    </div>
  );
}
