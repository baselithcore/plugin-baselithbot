import { useState } from 'react';
import { createPortal } from 'react-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { FileText } from 'lucide-react';
import type { ChatSource } from '@/lib/types';

interface Props {
  children: string;
  /** Map of citation number → source, enabling clickable inline `[n]` badges. */
  citations?: Record<number, ChatSource>;
  /** Open the cited note. */
  onCite?: (id: string) => void;
}

/**
 * Compact GFM markdown renderer for assistant messages. Styling lives in the
 * `.bb-md` scope (index.css). When `citations` are supplied, inline `[n]`
 * markers are rewritten to clickable badges that preview the source on hover
 * and open the note on click (modern RAG-citation UX).
 */
export function Markdown({ children, citations, onCite }: Props) {
  const text = citations
    ? children.replace(/\[(\d+)\]/g, (m, n) => (citations[+n] ? `[${m}](#cite-${n})` : m))
    : children;

  return (
    <div className="bb-md">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          a: ({ href, children: c }) => {
            const cite = /^#cite-(\d+)$/.exec(href || '');
            if (cite && citations) {
              const src = citations[+cite[1]];
              if (src) return <Citation source={src} onClick={() => onCite?.(src.id)} />;
            }
            return (
              <a href={href} target="_blank" rel="noreferrer noopener">
                {c}
              </a>
            );
          },
        }}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}

const POPOVER_W = 264;

/** Inline citation badge with a hover/focus preview of the source excerpt.
 *
 * The preview renders in a body-level portal at fixed, viewport-clamped
 * coordinates so it can never be clipped by the chat's scroll container
 * (an `overflow-y:auto` ancestor also clips overflow-x). */
function Citation({ source, onClick }: { source: ChatSource; onClick: () => void }) {
  const [box, setBox] = useState<DOMRect | null>(null);

  const place = (el: HTMLElement | null) => {
    if (el) setBox(el.getBoundingClientRect());
  };

  const left = box
    ? Math.min(
        Math.max(8, box.left + box.width / 2 - POPOVER_W / 2),
        window.innerWidth - POPOVER_W - 8
      )
    : 0;
  const above = box ? box.top > 180 : true;

  return (
    <span className="relative inline-block align-baseline">
      <button
        onClick={onClick}
        onMouseEnter={(e) => place(e.currentTarget)}
        onMouseLeave={() => setBox(null)}
        onFocus={(e) => place(e.currentTarget)}
        onBlur={() => setBox(null)}
        className="mx-0.5 rounded bg-[var(--color-accent-soft)] px-1 align-super text-[10px] font-semibold text-[var(--color-link)] transition hover:brightness-110"
      >
        {source.n}
      </button>
      {box &&
        createPortal(
          <div
            className="bb-pop pointer-events-none fixed z-[60] rounded-lg border border-[var(--color-border)] bg-[var(--color-elevated)] p-2.5 text-left shadow-xl"
            style={{
              width: POPOVER_W,
              left,
              ...(above
                ? { top: box.top - 8, transform: 'translateY(-100%)' }
                : { top: box.bottom + 8 }),
            }}
          >
            <span className="mb-1 flex items-center gap-1 text-xs font-semibold text-[var(--color-text)]">
              <FileText className="size-3 shrink-0 text-[var(--color-accent)]" />
              {source.title}
            </span>
            <span className="block text-[11px] leading-snug text-[var(--color-muted)]">
              {source.snippet || 'Open note →'}
            </span>
          </div>,
          document.body
        )}
    </span>
  );
}
