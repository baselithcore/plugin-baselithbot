import { useEffect, useMemo, useRef } from 'react';
import { marked } from 'marked';
import DOMPurify from 'dompurify';

marked.setOptions({ breaks: true, gfm: true });

export function Markdown({
  source,
  onCitationClick,
  citationLabels,
  className,
}: {
  source: string;
  onCitationClick?: (id: string) => void;
  citationLabels?: Map<string, string>;
  className?: string;
}) {
  const fragment = useMemo(() => {
    const parsed = marked.parse(source ?? '', { async: false }) as string;
    // DOMPurify with RETURN_DOM_FRAGMENT yields a sanitized DocumentFragment —
    // no innerHTML/dangerouslySetInnerHTML required.
    const frag = DOMPurify.sanitize(parsed, {
      ADD_ATTR: ['target', 'rel'],
      RETURN_DOM_FRAGMENT: true,
    }) as DocumentFragment;
    // Replace <code> spans with citation buttons (still in-tree, no string concat).
    frag.querySelectorAll('code').forEach((el) => {
      const id = el.textContent ?? '';
      const label = citationLabels?.get(id);
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.dataset.cite = id;
      btn.className = 'ra-cite';
      btn.textContent = label && label !== id ? label : id;
      if (label && label !== id) btn.title = id;
      el.replaceWith(btn);
    });
    return frag;
  }, [source, citationLabels]);

  const ref = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    const host = ref.current;
    if (!host) return;
    host.replaceChildren(fragment.cloneNode(true));
  }, [fragment]);

  return (
    <div
      ref={ref}
      className={`ra-md ${className ?? ''}`}
      onClick={(e) => {
        const t = e.target as HTMLElement;
        const cite = t.closest<HTMLElement>('[data-cite]');
        if (cite && onCitationClick) {
          e.preventDefault();
          onCitationClick(cite.dataset.cite ?? '');
        }
      }}
    />
  );
}
