// Markdown <-> editor boundary transforms.
//
// tiptap-markdown parses by rendering Markdown to HTML (markdown-it, html:true)
// then loading it through the schema, and serializes via per-node storage. A few
// constructs need help at the string boundary:
//   • `[[wikilinks]]`  → anchor HTML the WikiLink node parses (serialize: node).
//   • `==highlight==`  → <mark> (markdown-it has no `==` rule); serialize: mark.
//   • asset paths      → portable `_assets/<name>` on disk ⇄ servable URL in the
//                        editor, so the vault stays Obsidian-compatible.

const WIKILINK_RE = /\[\[([^\]\|#]+)(?:#[^\]\|]+)?(?:\|([^\]]+))?\]\]/g;
const HIGHLIGHT_RE = /==([^=\n]+)==/g;
const BASE = (import.meta.env.BASE_URL || '/').replace(/\/$/, '');

export function slugify(text: string): string {
  return text
    .toLowerCase()
    .normalize('NFKD')
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/** Disk Markdown → editor input: expand wikilinks, highlights and asset URLs. */
export function markdownToEditor(markdown: string): string {
  return markdown
    .replace(WIKILINK_RE, (_m, rawTarget: string, alias?: string) => {
      const target = slugify(rawTarget.trim());
      const label = (alias || rawTarget).trim();
      return `<a data-wikilink data-target="${escapeHtml(target)}">${escapeHtml(label)}</a>`;
    })
    .replace(HIGHLIGHT_RE, (_m, text: string) => `<mark>${escapeHtml(text)}</mark>`)
    .replace(/\]\(_assets\//g, `](${BASE}/api/assets/`);
}

/** Editor Markdown → disk: collapse servable asset URLs back to `_assets/<name>`. */
export function editorToMarkdown(markdown: string): string {
  const escaped = BASE.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return markdown
    .replace(new RegExp(`\\]\\(${escaped}/api/assets/`, 'g'), '](_assets/')
    .replace(/\]\(api\/assets\//g, '](_assets/');
}
