/**
 * Estrae uno snippet del body markdown attorno a un'ancora.
 *
 * Usato dal popover di citazione (CitationPopover) per mostrare il
 * pezzetto di documento citato senza dover aprire il drawer completo.
 */
export interface Excerpt {
  text: string;
  match: string | null;
  truncatedStart: boolean;
  truncatedEnd: boolean;
}

const FRONTMATTER_RE = /^---\s*\r?\n[\s\S]*?\r?\n---\s*\r?\n+/;
const FENCE_WRAP_RE = /^\s*```(?:markdown|md)?\s*\r?\n([\s\S]*?)\r?\n```\s*$/;

function stripFrontmatter(body: string): string {
  return body.replace(FRONTMATTER_RE, '');
}

function unwrapFence(body: string): string {
  const m = body.match(FENCE_WRAP_RE);
  return m ? m[1] : body;
}

function sanitize(body: string): string {
  let out = stripFrontmatter(body);
  out = unwrapFence(out.trim());
  out = stripFrontmatter(out);
  return out;
}

function buildAnchorRegex(anchor: string): RegExp | null {
  const cleaned = anchor.trim().replace(/[-_]+/g, ' ').replace(/\s+/g, ' ');
  if (!cleaned) return null;
  const escaped = cleaned
    .split(' ')
    .map((tok) => tok.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
    .join('[\\s\\-_]*');
  try {
    return new RegExp(escaped, 'i');
  } catch {
    return null;
  }
}

export function buildExcerpt(
  body: string,
  anchor: string | null | undefined,
  windowSize = 360
): Excerpt {
  const cleaned = sanitize(body).trimStart();
  if (anchor) {
    const re = buildAnchorRegex(anchor);
    if (re) {
      const found = re.test(cleaned) ? cleaned.match(re) : null;
      if (found && found.index !== undefined) {
        const idx = found.index;
        const half = Math.floor(windowSize / 2);
        const start = Math.max(0, idx - half);
        const end = Math.min(cleaned.length, idx + found[0].length + half);
        return {
          text: cleaned.slice(start, end).trim(),
          match: found[0],
          truncatedStart: start > 0,
          truncatedEnd: end < cleaned.length,
        };
      }
    }
  }
  return {
    text: cleaned.slice(0, windowSize).trim(),
    match: null,
    truncatedStart: false,
    truncatedEnd: cleaned.length > windowSize,
  };
}
