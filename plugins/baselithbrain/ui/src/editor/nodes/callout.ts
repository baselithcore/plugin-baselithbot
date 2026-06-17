import { Extension } from '@tiptap/core';
import { Plugin } from '@tiptap/pm/state';
import { Decoration, DecorationSet } from '@tiptap/pm/view';
import type { Node as PMNode } from '@tiptap/pm/model';

// Callouts are plain blockquotes whose first line is Obsidian's `[!kind] …`
// admonition marker. We never introduce a new node — we only *decorate* such
// blockquotes with a class so they render with an accent + icon. This keeps the
// Markdown 100% lossless and portable (Obsidian renders the same callouts).

const KNOWN = new Set([
  'note',
  'info',
  'tip',
  'todo',
  'abstract',
  'question',
  'warning',
  'caution',
  'danger',
  'success',
  'quote',
  'example',
]);
const MARKER = /^\s*\[!(\w+)\]/i;

function calloutKind(blockquote: PMNode): string | null {
  const first = blockquote.firstChild;
  const match = first?.textContent.match(MARKER);
  if (!match) return null;
  const kind = match[1].toLowerCase();
  return KNOWN.has(kind) ? kind : 'note';
}

function decorate(doc: PMNode): DecorationSet {
  const decos: Decoration[] = [];
  doc.descendants((node, pos) => {
    if (node.type.name !== 'blockquote') return;
    const kind = calloutKind(node);
    if (kind) {
      decos.push(
        Decoration.node(pos, pos + node.nodeSize, {
          class: `bb-callout bb-callout-${kind}`,
          'data-callout': kind,
        })
      );
    }
  });
  return DecorationSet.create(doc, decos);
}

/** Decorates `> [!kind] …` blockquotes as styled callouts (no schema change). */
export const Callout = Extension.create({
  name: 'calloutDecoration',
  addProseMirrorPlugins() {
    return [
      new Plugin({
        state: {
          init: (_, { doc }) => decorate(doc),
          apply: (tr, old) => (tr.docChanged ? decorate(tr.doc) : old),
        },
        props: {
          decorations(state) {
            return this.getState(state);
          },
        },
      }),
    ];
  },
});
