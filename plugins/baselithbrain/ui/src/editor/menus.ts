// Headless controller for the two in-editor popovers: the '/' slash command
// menu and the '[[' wikilink autocomplete. Kept framework-light: it inspects
// the ProseMirror selection on every transaction and exposes plain state plus
// a keydown handler the Editor wires to the DOM. No tippy/suggestion plugin —
// fully under our control, easy to build and test.
import { useEffect, useState, useCallback } from 'react';
import type { Editor } from '@tiptap/react';
import { pickAndUploadImage } from './imageUpload';

export interface SlashCommand {
  id: string;
  label: string;
  hint: string;
  group: string;
  run: (editor: Editor) => void;
}

const insertCallout = (e: Editor) =>
  e
    .chain()
    .focus()
    .insertContent({
      type: 'blockquote',
      content: [{ type: 'paragraph', content: [{ type: 'text', text: '[!note] ' }] }],
    })
    .run();

// Grouped so each section honors the "≤5 per level" menu rule.
export const SLASH_COMMANDS: SlashCommand[] = [
  {
    id: 'h1',
    label: 'Heading 1',
    hint: '#',
    group: 'Basic',
    run: (e) => e.chain().focus().toggleHeading({ level: 1 }).run(),
  },
  {
    id: 'h2',
    label: 'Heading 2',
    hint: '##',
    group: 'Basic',
    run: (e) => e.chain().focus().toggleHeading({ level: 2 }).run(),
  },
  {
    id: 'h3',
    label: 'Heading 3',
    hint: '###',
    group: 'Basic',
    run: (e) => e.chain().focus().toggleHeading({ level: 3 }).run(),
  },
  {
    id: 'todo',
    label: 'To-do',
    hint: '[ ]',
    group: 'Lists',
    run: (e) => e.chain().focus().toggleTaskList().run(),
  },
  {
    id: 'bullet',
    label: 'Bullet list',
    hint: '-',
    group: 'Lists',
    run: (e) => e.chain().focus().toggleBulletList().run(),
  },
  {
    id: 'ordered',
    label: 'Numbered list',
    hint: '1.',
    group: 'Lists',
    run: (e) => e.chain().focus().toggleOrderedList().run(),
  },
  {
    id: 'quote',
    label: 'Quote',
    hint: '"',
    group: 'Blocks',
    run: (e) => e.chain().focus().toggleBlockquote().run(),
  },
  { id: 'callout', label: 'Callout', hint: '!', group: 'Blocks', run: insertCallout },
  {
    id: 'code',
    label: 'Code block',
    hint: '```',
    group: 'Blocks',
    run: (e) => e.chain().focus().toggleCodeBlock().run(),
  },
  {
    id: 'table',
    label: 'Table',
    hint: '⊞',
    group: 'Insert',
    run: (e) => e.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run(),
  },
  { id: 'image', label: 'Image', hint: '🖼', group: 'Insert', run: (e) => pickAndUploadImage(e) },
  {
    id: 'divider',
    label: 'Divider',
    hint: '---',
    group: 'Insert',
    run: (e) => e.chain().focus().setHorizontalRule().run(),
  },
];

export interface MenuState {
  kind: 'slash' | 'link' | null;
  query: string;
  index: number;
  coords: { left: number; top: number } | null;
  from: number; // position where the trigger token starts (query start)
  trigger: 'bracket' | 'at'; // which char opened the link menu (sets delete width)
}

const EMPTY: MenuState = {
  kind: null,
  query: '',
  index: 0,
  coords: null,
  from: 0,
  trigger: 'bracket',
};

export function useEditorMenus(editor: Editor | null) {
  const [state, setState] = useState<MenuState>(EMPTY);
  const close = useCallback(() => setState(EMPTY), []);

  useEffect(() => {
    if (!editor) return;
    const onUpdate = () => {
      const { state: s } = editor;
      const { from, empty } = s.selection;
      if (!empty) return setState(EMPTY);
      const $from = s.selection.$from;
      const before = $from.parent.textBetween(0, $from.parentOffset, '\n', '\0');

      const link = before.match(/\[\[([^\]]*)$/);
      if (link) {
        const start = from - link[1].length;
        return setState((p) => ({
          kind: 'link',
          query: link[1],
          index: p.kind === 'link' ? p.index : 0,
          coords: coordsAt(editor, start),
          from: start,
          trigger: 'bracket',
        }));
      }
      const at = before.match(/(?:^|\s)@([\w-]*)$/);
      if (at) {
        const start = from - at[1].length;
        return setState((p) => ({
          kind: 'link',
          query: at[1],
          index: p.kind === 'link' ? p.index : 0,
          coords: coordsAt(editor, start),
          from: start,
          trigger: 'at',
        }));
      }
      const slash = before.match(/(?:^|\s)\/(\w*)$/);
      if (slash) {
        const start = from - slash[1].length - 1;
        return setState((p) => ({
          kind: 'slash',
          query: slash[1],
          index: p.kind === 'slash' ? p.index : 0,
          coords: coordsAt(editor, start),
          from: start,
          trigger: 'bracket',
        }));
      }
      setState(EMPTY);
    };
    editor.on('selectionUpdate', onUpdate);
    editor.on('update', onUpdate);
    return () => {
      editor.off('selectionUpdate', onUpdate);
      editor.off('update', onUpdate);
    };
  }, [editor]);

  const move = useCallback((delta: number, len: number) => {
    setState((p) => ({ ...p, index: (p.index + delta + len) % len }));
  }, []);

  return { state, close, move, setState };
}

function coordsAt(editor: Editor, pos: number): { left: number; top: number } {
  const c = editor.view.coordsAtPos(Math.max(0, pos));
  return { left: c.left, top: c.bottom };
}
