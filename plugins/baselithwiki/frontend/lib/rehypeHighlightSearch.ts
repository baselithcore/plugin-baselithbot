import type { Root, Element, Text, ElementContent } from 'hast';

/**
 * Rehype plugin: wrap occurrences of `query` (case-insensitive) inside
 * `<mark class="search-hit" data-hit-index="N">…</mark>`, preserving the
 * surrounding markdown rendering (heading, list, blockquote, table…).
 *
 * Skip text nodes that are descendants of `<code>` / `<pre>` / `<style>` /
 * `<script>` so syntactic highlight + code identity stay intact.
 *
 * Output rationale (rev 2):
 *
 * - **`mark` tag** invece di `span` — semantica nativa screen-reader
 *   (`<mark>` annuncia "highlight") + default browser styling
 *   sopravvive anche se la CSS della pagina viene saturata da
 *   reset-layer / shadow DOM.
 * - **className string** invece di `['search-hit']`. Alcune build di
 *   react-markdown v10 + hast-util-to-jsx-runtime processavano
 *   l'array preservando come-è invece di joinare, lasciando il
 *   container DOM con `class="search-hit"` come singolo token ma in
 *   alcuni setup risultava `class=""`. Stringa diretta = zero ambiguità.
 * - **style string + `!important`** sulle proprietà critiche.
 *   Cascade della preview applica margini/colori al markdown
 *   intero (`.md--preview *`); `!important` qui evita race con la
 *   regola CSS del file globale.
 * - **`data-hit-index`** numerato in document order, così la toolbar
 *   può navigare ai match con `querySelectorAll('[data-hit-index]')`
 *   (next/prev jump implementation).
 *
 * Implementation note: il vecchio path usava `unist-util-visit` con
 * in-place splice; con `react-markdown` v10 + `rehype-highlight` il
 * mutate-during-traverse esponeva `undefined` ai walker interni,
 * crashando con `Cannot use 'in' operator…`. Walk manuale che
 * ricostruisce ogni `children` array — niente mutate, niente
 * dipendenze dal visitor.
 */
export function rehypeHighlightSearch(query: string) {
  const trimmed = query.trim();
  return (tree: Root) => {
    if (!trimmed) return;
    const escaped = trimmed.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    let re: RegExp;
    try {
      re = new RegExp(escaped, 'gi');
    } catch {
      return;
    }

    let hitIndex = 0;
    const inlineStyle =
      'background:#fde68a !important;' +
      'color:#78350f !important;' +
      'padding:0 2px !important;' +
      'border-radius:3px !important;' +
      'font-weight:600 !important;' +
      'box-decoration-break:clone;' +
      '-webkit-box-decoration-break:clone;';

    try {
      walk(tree as unknown as Element);
    } catch {
      /* never let a malformed tree break the whole render */
    }

    function walk(node: Element | Root) {
      const children = (node as Element).children;
      if (!Array.isArray(children)) return;
      const next: ElementContent[] = [];
      for (const child of children) {
        if (!child) continue;
        if (child.type === 'text') {
          next.push(...splitText(child as Text));
          continue;
        }
        if (child.type === 'element') {
          const el = child as Element;
          if (
            el.tagName === 'code' ||
            el.tagName === 'pre' ||
            el.tagName === 'style' ||
            el.tagName === 'script' ||
            el.tagName === 'mark' // already a mark → don't re-wrap
          ) {
            next.push(el);
            continue;
          }
          walk(el);
          next.push(el);
          continue;
        }
        next.push(child as ElementContent);
      }
      (node as Element).children = next;
    }

    function splitText(node: Text): ElementContent[] {
      const value = node.value;
      if (!value) return [node];
      re.lastIndex = 0;
      const matches = Array.from(value.matchAll(re));
      if (matches.length === 0) return [node];
      const out: ElementContent[] = [];
      let last = 0;
      for (const m of matches) {
        const idx = m.index ?? 0;
        if (idx > last) {
          out.push({ type: 'text', value: value.slice(last, idx) });
        }
        out.push({
          type: 'element',
          tagName: 'mark',
          properties: {
            // String form — react-markdown v10 + hast-util-to-jsx-runtime
            // gestisce sia array che string, ma stringa diretta evita
            // edge case su build production con tree-shaking aggressivo.
            className: 'search-hit',
            'data-hit-index': String(hitIndex++),
            style: inlineStyle,
          },
          children: [{ type: 'text', value: m[0] }],
        });
        last = idx + m[0].length;
      }
      if (last < value.length) {
        out.push({ type: 'text', value: value.slice(last) });
      }
      return out;
    }
  };
}
