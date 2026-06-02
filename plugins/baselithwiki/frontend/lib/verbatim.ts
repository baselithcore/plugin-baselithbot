export interface Verbatim {
  kind: 'quote' | 'rule' | 'important' | 'warning';
  header: string;
  body: string;
  articleRef?: string;
}

const CALLOUT_RE = /^> \[!(quote|rule|important|warning)\](.*)$/i;
const ARTICLE_RE = /\b(art\.?\s*\d+(?:[.\-]\d+)*(?:\s*(?:lett|comma)\.?\s*[a-z0-9]+)?[^,\n)]*)/i;

export function extractVerbatims(body: string): Verbatim[] {
  const lines = body.split(/\r?\n/);
  const out: Verbatim[] = [];
  let current: Verbatim | null = null;
  let bodyLines: string[] = [];

  const flush = () => {
    if (current) {
      current.body = bodyLines.join('\n').trim();
      if (current.body || current.header) out.push(current);
    }
    current = null;
    bodyLines = [];
  };

  for (const raw of lines) {
    const m = raw.match(CALLOUT_RE);
    if (m) {
      flush();
      const kind = m[1].toLowerCase() as Verbatim['kind'];
      const header = m[2].trim();
      const artMatch = header.match(ARTICLE_RE);
      current = {
        kind,
        header,
        body: '',
        articleRef: artMatch?.[1]?.trim(),
      };
      continue;
    }
    if (current) {
      if (/^>\s?/.test(raw)) {
        bodyLines.push(raw.replace(/^>\s?/, ''));
      } else if (raw.trim() === '') {
        bodyLines.push('');
      } else {
        flush();
      }
    }
  }
  flush();
  return out;
}

export function findVerbatimByArticle(verbatims: Verbatim[], anchor?: string): Verbatim | null {
  if (!anchor) return null;
  const normAnchor = anchor.toLowerCase().replace(/[-_\s]/g, '');
  for (const v of verbatims) {
    const hay = (v.header + ' ' + (v.articleRef ?? '')).toLowerCase().replace(/[-_\s.]/g, '');
    if (hay.includes(normAnchor)) return v;
  }
  return null;
}
