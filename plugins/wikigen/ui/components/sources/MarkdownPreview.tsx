import { useDeferredValue, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import remarkGfm from 'remark-gfm';
import { rehypeHighlightSearch } from '../../lib/rehypeHighlightSearch';

// Sotto questa soglia, l'highlight produrrebbe centinaia di match per
// keystroke (es. "e" matcha ~ogni parola) saturando il DOM e congelando
// la preview. Niente highlight per query troppo corte; il conteggio hit
// nella toolbar resta comunque accurato (è calcolato a parte).
const MIN_HIGHLIGHT_LEN = 2;

/**
 * Rendering preview del corpo markdown.
 *
 * - Markdown nativo (heading, list, table, blockquote, code) via
 *   react-markdown + remark-gfm + rehype-highlight.
 * - Search highlight sul filtro `query` via plugin rehype custom che
 *   avvolge le occorrenze in `<mark class="search-hit">` preservando
 *   la struttura del documento (no più dump in `<pre>`).
 * - Wikilink Obsidian `[[folder/slug]]` convertiti a link interni
 *   `wiki://…` che il consumer (Sources drawer) può intercettare.
 * - Limite di caratteri per perf su pagine grosse.
 */
const WIKILINK_PREVIEW_RE = /\[\[([^\]|#]+)(?:#([^\]|]+))?(?:\|([^\]]+))?\]\]/g;

function transformWikilinks(md: string): string {
  return md.replace(WIKILINK_PREVIEW_RE, (_m, target: string, _anchor, alias?: string) => {
    const label = (alias ?? target).trim();
    const href = `wiki://${encodeURIComponent(target.trim())}`;
    return `[${label}](${href})`;
  });
}

const FRONTMATTER_RE = /^---\s*\r?\n[\s\S]*?\r?\n---\s*\r?\n?/;
const OPEN_FENCE_RE = /^```(?:markdown|md)\s*$/;
const CLOSE_FENCE_RE = /^```\s*$/;

// Generator outputs occasionally wrap the entire planner template in a
// ```markdown … ``` fence with nested ```sh blocks inside. Strip the
// outer wrapper line-by-line so nested code blocks survive intact.
function unwrapMarkdownFence(md: string): string {
  const lines = md.split('\n');
  let start = 0;
  while (start < lines.length && lines[start].trim() === '') start++;
  if (start >= lines.length || !OPEN_FENCE_RE.test(lines[start].trim())) return md;
  let end = lines.length - 1;
  while (end > start && !CLOSE_FENCE_RE.test(lines[end].trim())) end--;
  if (end <= start) return md;
  const head = lines.slice(0, start);
  const inner = lines.slice(start + 1, end);
  const tail = lines.slice(end + 1);
  return [...head, ...inner, ...tail].join('\n');
}

function sanitizeBody(md: string): string {
  let out = md.replace(FRONTMATTER_RE, '');
  out = unwrapMarkdownFence(out);
  out = out.replace(FRONTMATTER_RE, '');
  return out;
}

export function MarkdownPreview({
  body,
  query,
  limit,
}: {
  body: string;
  query: string;
  limit: number;
}) {
  const text = useMemo(() => {
    const cleaned = sanitizeBody(body);
    const sliced = cleaned.length > limit ? cleaned.slice(0, limit) : cleaned;
    return transformWikilinks(sliced);
  }, [body, limit]);
  // deferred + min-length: l'highlight non corre per ogni keystroke,
  // così la preview non si blocca mentre l'utente digita.
  const deferredQuery = useDeferredValue(query);
  const effectiveQuery = deferredQuery.trim().length >= MIN_HIGHLIGHT_LEN ? deferredQuery : '';
  const plugins = useMemo(
    () => [rehypeHighlight, rehypeHighlightSearch(effectiveQuery)],
    [effectiveQuery]
  );
  return (
    <div className="md md--preview text-[12px] leading-relaxed">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={plugins}
        components={{
          a({ href, children, ...rest }) {
            if (href?.startsWith('wiki://')) {
              return (
                <span className="wikilink-inline" title={decodeURIComponent(href.slice(7))}>
                  {children}
                </span>
              );
            }
            return (
              <a href={href} target="_blank" rel="noreferrer" {...rest}>
                {children}
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
