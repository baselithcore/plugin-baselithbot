import { useEffect, useRef, useState } from 'react';
import type { Citation } from '../lib/citations';
import { cn } from '../lib/cn';
import { loadPage } from '../lib/pageCache';
import { CitationPopover } from './CitationPopover';

interface Props {
  citation: Citation;
  onOpen: (docId: string, anchor?: string) => void;
  active?: boolean;
}

const HOVER_OPEN_DELAY = 180;
const HOVER_CLOSE_DELAY = 140;

/**
 * Superscript "[n]" inline cliccabile — stile NotebookLM:
 * - hover/focus → popover con titolo + excerpt attorno all'ancora
 * - click → apre pannello fonti completo (drawer destro)
 *
 * Il popover prefetcha la pagina al primo hover e la mette in cache
 * (lib/pageCache) così il drawer e gli hover successivi sono istantanei.
 */
export function CitationBadge({ citation, onOpen, active }: Props) {
  const { n, source, anchor, label } = citation;
  const hasSource = source !== null;
  const btnRef = useRef<HTMLButtonElement>(null);
  const openTimer = useRef<number | null>(null);
  const closeTimer = useRef<number | null>(null);
  const [popoverOpen, setPopoverOpen] = useState(false);

  const titleBits = [
    source?.title ?? label,
    anchor ? `#${anchor}` : null,
    source?.edizione ? `Ed. ${source.edizione}` : null,
    !hasSource ? '(fonte non tra i risultati)' : null,
  ].filter(Boolean) as string[];

  const clearTimers = () => {
    if (openTimer.current) {
      window.clearTimeout(openTimer.current);
      openTimer.current = null;
    }
    if (closeTimer.current) {
      window.clearTimeout(closeTimer.current);
      closeTimer.current = null;
    }
  };

  useEffect(() => () => clearTimers(), []);

  const scheduleOpen = () => {
    if (!hasSource) return;
    clearTimers();
    // prefetch parallelo al timer di apertura
    if (source?.document_id) loadPage(source.document_id).catch(() => {});
    openTimer.current = window.setTimeout(() => setPopoverOpen(true), HOVER_OPEN_DELAY);
  };
  const scheduleClose = () => {
    clearTimers();
    closeTimer.current = window.setTimeout(() => setPopoverOpen(false), HOVER_CLOSE_DELAY);
  };

  const handleClick = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (!hasSource) return;
    setPopoverOpen(false);
    onOpen(source!.document_id, anchor);
  };

  return (
    <>
      <button
        ref={btnRef}
        type="button"
        onClick={handleClick}
        onMouseEnter={scheduleOpen}
        onMouseLeave={scheduleClose}
        onFocus={scheduleOpen}
        onBlur={scheduleClose}
        disabled={!hasSource}
        aria-haspopup="dialog"
        aria-expanded={popoverOpen}
        className={cn(
          'citation-ref focus-ring',
          active && 'citation-ref--active',
          !hasSource && 'citation-ref--orphan'
        )}
        title={titleBits.join(' · ')}
        aria-label={`citazione ${n}: ${titleBits.join(', ')}`}
      >
        {n}
      </button>
      {hasSource && (
        <span
          onMouseEnter={() => clearTimers()}
          onMouseLeave={scheduleClose}
        >
          <CitationPopover
            citation={citation}
            anchorEl={btnRef.current}
            open={popoverOpen}
            onOpenSource={() => {
              setPopoverOpen(false);
              onOpen(source!.document_id, anchor);
            }}
            onClose={() => setPopoverOpen(false)}
          />
        </span>
      )}
    </>
  );
}
