import type { Source } from './types';

/**
 * Citazione inline numerata che compare nel testo della risposta.
 * L'ordine `n` riflette la comparsa nel testo (prima menzione = [1]).
 */
export interface Citation {
  n: number;
  docId: string;
  anchor?: string;
  label: string;
  source: Source | null;
}

export interface CitationResult {
  content: string;
  citations: Citation[];
}

const WIKILINK_RE = /\[\[([^\]|#]+)(?:#([^\]|]+))?(?:\|([^\]]+))?\]\]/g;

function normalizeTarget(t: string): string {
  return t.trim().replace(/\.md$/i, '').toLowerCase();
}

function findSource(target: string, sources: Source[]): Source | null {
  const norm = normalizeTarget(target);
  const exact = sources.find((s) => normalizeTarget(s.document_id) === norm);
  if (exact) return exact;
  const suffix = sources.find((s) => normalizeTarget(s.document_id).endsWith(norm));
  if (suffix) return suffix;
  const byTitle = sources.find((s) => s.title.toLowerCase() === norm.replace(/-/g, ' '));
  return byTitle ?? null;
}

// Trailing "Fonti:" / "Sources:" block emesso dall'LLM in fondo alla
// risposta. Duplica il footer fonti renderizzato dal client (badge +
// titolo + rango + edizione). Strip per evitare doppia citazione.
const TRAILING_SOURCES_RE =
  /(?:\n|^)(?:#{1,6}\s*)?(?:\*{1,2})?(?:Fonti(?:\s+citate)?|Sources)(?:\*{1,2})?:?\s*\n(?:\s*[-*]\s+.+(?:\n|$))+\s*$/i;

export function stripTrailingSourcesBlock(content: string): string {
  return content.replace(TRAILING_SOURCES_RE, '');
}

export function prepareCitations(content: string, sources: Source[]): CitationResult {
  const seen = new Map<string, Citation>();
  let counter = 0;

  const prepared = content.replace(
    WIKILINK_RE,
    (_m, target: string, anchor?: string, alias?: string) => {
      const docId = normalizeTarget(target);
      const key = anchor ? `${docId}#${anchor}` : docId;
      let cit = seen.get(key);
      if (!cit) {
        counter += 1;
        cit = {
          n: counter,
          docId,
          anchor: anchor?.trim(),
          label: (alias ?? target).trim(),
          source: findSource(target, sources),
        };
        seen.set(key, cit);
      }
      return `[CIT:${cit.n}]`;
    }
  );

  return {
    content: prepared,
    citations: Array.from(seen.values()).sort((a, b) => a.n - b.n),
  };
}

export function splitCitationTokens(
  text: string,
  citations: Citation[]
): Array<{ type: 'text'; value: string } | { type: 'cit'; citation: Citation }> {
  const TOKEN_RE = /\[CIT:(\d+)\]/g;
  const out: Array<{ type: 'text'; value: string } | { type: 'cit'; citation: Citation }> = [];
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = TOKEN_RE.exec(text))) {
    if (m.index > last) out.push({ type: 'text', value: text.slice(last, m.index) });
    const n = Number(m[1]);
    const cit = citations.find((c) => c.n === n);
    if (cit) out.push({ type: 'cit', citation: cit });
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push({ type: 'text', value: text.slice(last) });
  return out;
}
