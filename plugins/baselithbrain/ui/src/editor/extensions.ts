import StarterKit from '@tiptap/starter-kit';
import Placeholder from '@tiptap/extension-placeholder';
import TaskList from '@tiptap/extension-task-list';
import TaskItem from '@tiptap/extension-task-item';
import Image from '@tiptap/extension-image';
import Link from '@tiptap/extension-link';
import CodeBlockLowlight from '@tiptap/extension-code-block-lowlight';
import GlobalDragHandle from 'tiptap-extension-global-drag-handle';
import { createLowlight, common } from 'lowlight';
import { Markdown } from 'tiptap-markdown';
import type { Extensions } from '@tiptap/core';
import { WikiLink } from './wikilink';
import { HighlightMark } from './nodes/highlight';
import { Callout } from './nodes/callout';
import { TableKit } from './nodes/table';

const lowlight = createLowlight(common);

/**
 * Editor extension set: block-based StarterKit (its plain code block swapped for
 * a syntax-highlighted one) + tasks, tables, images, `==highlight==`, callout
 * decoration, a global drag handle to reorder blocks, the `[[wikilink]]` node,
 * and Markdown round-trip (html:true so wikilink/mark anchors survive).
 * Pure factory so the Editor component stays presentation-only.
 */
export function buildExtensions(): Extensions {
  return [
    StarterKit.configure({
      heading: { levels: [1, 2, 3] },
      codeBlock: false,
    }),
    CodeBlockLowlight.configure({
      lowlight,
      HTMLAttributes: { spellcheck: 'false' },
    }),
    TaskList,
    TaskItem.configure({ nested: true }),
    ...TableKit,
    Image.configure({ inline: false, allowBase64: false }),
    Link.configure({
      openOnClick: false,
      autolink: true,
      HTMLAttributes: { rel: 'noreferrer noopener', target: '_blank' },
    }),
    HighlightMark,
    Callout,
    WikiLink,
    GlobalDragHandle.configure({ dragHandleWidth: 20, scrollTreshold: 100 }),
    Placeholder.configure({
      placeholder: "Write, or press '/' for blocks · '[[' or '@' to link…",
    }),
    Markdown.configure({
      html: true,
      tightLists: true,
      bulletListMarker: '-',
      transformPastedText: true,
      transformCopiedText: true,
    }),
  ];
}
