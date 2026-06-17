import { Node, mergeAttributes } from '@tiptap/core';

export interface WikiLinkAttrs {
  target: string;
  label?: string | null;
}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    wikiLink: {
      insertWikiLink: (attrs: WikiLinkAttrs) => ReturnType;
    };
  }
}

/**
 * Inline atom node for `[[wikilinks]]`.
 *
 * - Renders as a styled, clickable chip (`a.bb-wikilink`) carrying the resolved
 *   `data-target` (slug) and a display label.
 * - Serializes back to Markdown as `[[target]]` (or `[[target|label]]`) via the
 *   tiptap-markdown `addStorage().markdown` hook — so the on-disk format stays
 *   an open, portable wikilink, never proprietary state.
 * - Parsing from Markdown is handled at the string boundary (markdownBridge),
 *   which rewrites `[[..]]` to the matching anchor before `setContent`.
 */
export const WikiLink = Node.create({
  name: 'wikiLink',
  inline: true,
  group: 'inline',
  atom: true,
  selectable: true,

  addAttributes() {
    return {
      target: { default: '' },
      label: { default: null },
    };
  },

  parseHTML() {
    return [
      {
        tag: 'a[data-wikilink]',
        getAttrs: (el) => ({
          target: (el as HTMLElement).getAttribute('data-target') || '',
          label: (el as HTMLElement).textContent || null,
        }),
      },
    ];
  },

  renderHTML({ node, HTMLAttributes }) {
    const target = node.attrs.target as string;
    const label = (node.attrs.label as string | null) || target;
    return [
      'a',
      mergeAttributes(HTMLAttributes, {
        'data-wikilink': '',
        'data-target': target,
        class: 'bb-wikilink',
      }),
      label,
    ];
  },

  renderText({ node }) {
    return `[[${node.attrs.target}]]`;
  },

  addCommands() {
    return {
      insertWikiLink:
        (attrs) =>
        ({ commands }) =>
          commands.insertContent({ type: this.name, attrs }),
    };
  },

  addStorage() {
    return {
      markdown: {
        serialize(state: { write: (s: string) => void }, node: { attrs: WikiLinkAttrs }) {
          const { target, label } = node.attrs;
          state.write(label && label !== target ? `[[${target}|${label}]]` : `[[${target}]]`);
        },
        parse: {},
      },
    };
  },
});
