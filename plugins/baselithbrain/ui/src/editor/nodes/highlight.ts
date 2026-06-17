import Highlight from '@tiptap/extension-highlight';

/**
 * `==text==` highlight mark. Extends the base Highlight with a Markdown
 * serializer so it round-trips to Obsidian's `==…==` syntax (the matching
 * parse side is a pre-replace to `<mark>` in the markdown bridge, since
 * markdown-it has no `==` rule by default).
 */
export const HighlightMark = Highlight.extend({
  addStorage() {
    return {
      markdown: {
        serialize: { open: '==', close: '==', mixable: true, expelEnclosingWhitespace: true },
        parse: {},
      },
    };
  },
});
