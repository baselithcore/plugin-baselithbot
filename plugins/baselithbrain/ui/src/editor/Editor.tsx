import { useEffect, useRef, useCallback } from 'react';
import { EditorContent, useEditor } from '@tiptap/react';
import { buildExtensions } from './extensions';
import { markdownToEditor, editorToMarkdown, slugify } from './markdownBridge';
import { useEditorMenus, SLASH_COMMANDS, type SlashCommand } from './menus';
import { SlashMenu } from './SlashMenu';
import { LinkMenu, linkChoices, type LinkChoice } from './LinkMenu';
import { BubbleFormat } from './BubbleFormat';
import { uploadAndInsert, imageFilesFrom } from './imageUpload';
import { useBrain } from '@/store';
import { api } from '@/lib/api';

interface Props {
  noteId: string;
  body: string;
  onSaved: (note: import('@/lib/types').Note) => void;
}

const SAVE_DEBOUNCE = 600;

/**
 * TipTap block-based editor with Markdown round-trip, `[[` wikilink
 * autocomplete and a `/` slash menu. Body is the only field saved here (title
 * and tags live in the Topbar) — debounced, never on every keystroke.
 */
export function Editor({ noteId, body, onSaved }: Props) {
  const notes = useBrain((s) => s.notes);
  const openWiki = useBrain((s) => s.openWiki);
  const loadingRef = useRef(true);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const editor = useEditor({
    extensions: buildExtensions(),
    editorProps: {
      attributes: { class: 'bb-prose focus:outline-none' },
      handleClickOn: (_view, _pos, node) => {
        if (node.type.name === 'wikiLink') {
          void openWiki(node.attrs.target as string, node.attrs.label as string);
          return true;
        }
        return false;
      },
    },
  });

  const { state, close, move, setState } = useEditorMenus(editor);

  // Persist body (debounced) on edits, skipping the programmatic load.
  useEffect(() => {
    if (!editor) return;
    const onUpdate = () => {
      if (loadingRef.current) return;
      if (saveTimer.current) clearTimeout(saveTimer.current);
      saveTimer.current = setTimeout(async () => {
        const md = editorToMarkdown(editor.storage.markdown.getMarkdown());
        const saved = await api.updateNote(noteId, { body: md });
        onSaved(saved);
      }, SAVE_DEBOUNCE);
    };
    editor.on('update', onUpdate);
    return () => {
      editor.off('update', onUpdate);
    };
  }, [editor, noteId, onSaved]);

  // Image paste / drop → upload to the vault and insert at the caret.
  useEffect(() => {
    if (!editor) return;
    const dom = editor.view.dom;
    const onPaste = (e: ClipboardEvent) => {
      const files = imageFilesFrom(e.clipboardData?.items ?? null);
      if (files.length) {
        e.preventDefault();
        files.forEach((f) => void uploadAndInsert(editor, f));
      }
    };
    const onDrop = (e: DragEvent) => {
      const files = imageFilesFrom(e.dataTransfer?.items ?? null);
      if (files.length) {
        e.preventDefault();
        files.forEach((f) => void uploadAndInsert(editor, f));
      }
    };
    dom.addEventListener('paste', onPaste);
    dom.addEventListener('drop', onDrop);
    return () => {
      dom.removeEventListener('paste', onPaste);
      dom.removeEventListener('drop', onDrop);
    };
  }, [editor]);

  // Load note content when the active note changes.
  useEffect(() => {
    if (!editor) return;
    loadingRef.current = true;
    editor.commands.setContent(markdownToEditor(body), false);
    close();
    const t = setTimeout(() => (loadingRef.current = false), 0);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [editor, noteId]);

  const filteredSlash = SLASH_COMMANDS.filter((c) =>
    c.label.toLowerCase().includes(state.query.toLowerCase())
  );
  const choices = linkChoices(notes, state.query);

  const pickSlash = useCallback(
    (cmd: SlashCommand) => {
      if (!editor) return;
      const to = editor.state.selection.from;
      editor.chain().focus().deleteRange({ from: state.from, to }).run();
      cmd.run(editor);
      close();
    },
    [editor, state.from, close]
  );

  const pickLink = useCallback(
    (choice: LinkChoice) => {
      if (!editor) return;
      const to = editor.state.selection.from;
      // Delete the trigger token too: '[[' is 2 chars, '@' is 1.
      const triggerLen = state.trigger === 'at' ? 1 : 2;
      editor
        .chain()
        .focus()
        .deleteRange({ from: state.from - triggerLen, to })
        .insertWikiLink({ target: slugify(choice.title), label: choice.title })
        .insertContent(' ')
        .run();
      close();
    },
    [editor, state.from, state.trigger, close]
  );

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (!state.kind || !editor) return;
      const list = state.kind === 'slash' ? filteredSlash : choices;
      if (!list.length) return;
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        move(1, list.length);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        move(-1, list.length);
      } else if (e.key === 'Enter') {
        e.preventDefault();
        if (state.kind === 'slash') pickSlash(filteredSlash[state.index]);
        else pickLink(choices[state.index]);
      } else if (e.key === 'Escape') {
        e.preventDefault();
        close();
      }
    },
    [state, editor, filteredSlash, choices, move, pickSlash, pickLink, close]
  );

  // Clamp the highlighted index if the filtered list shrank.
  useEffect(() => {
    const len = state.kind === 'slash' ? filteredSlash.length : choices.length;
    if (state.kind && len && state.index >= len) {
      setState((p) => ({ ...p, index: len - 1 }));
    }
  }, [state.kind, state.index, filteredSlash.length, choices.length, setState]);

  // Click anywhere in the (tall) editor area focuses the document at its end —
  // otherwise only the single empty first line is clickable on a blank note.
  const focusFromBlank = useCallback(
    (e: React.MouseEvent) => {
      if (!editor || e.target !== e.currentTarget) return;
      editor.chain().focus('end').run();
    },
    [editor]
  );

  return (
    <div onKeyDown={onKeyDown} className="mx-auto w-full max-w-3xl px-2">
      <BubbleFormat editor={editor} />
      <div onClick={focusFromBlank} className="min-h-[60vh] cursor-text">
        <EditorContent editor={editor} />
      </div>
      {state.kind === 'slash' && state.coords && (
        <SlashMenu
          commands={filteredSlash}
          index={state.index}
          coords={state.coords}
          onPick={pickSlash}
        />
      )}
      {state.kind === 'link' && state.coords && (
        <LinkMenu
          notes={notes}
          query={state.query}
          index={state.index}
          coords={state.coords}
          onPick={pickLink}
        />
      )}
    </div>
  );
}
