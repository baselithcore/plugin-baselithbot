import { BubbleMenu, type Editor } from '@tiptap/react';
import {
  Bold,
  Italic,
  Strikethrough,
  Code,
  Highlighter,
  Heading1,
  Heading2,
  Quote,
  Link as LinkIcon,
} from 'lucide-react';
import { cn } from '@/lib/cn';

interface Props {
  editor: Editor | null;
}

interface Action {
  id: string;
  icon: typeof Bold;
  title: string;
  isActive: () => boolean;
  run: () => void;
}

/** Selection toolbar: block transforms + inline formatting over highlighted text. */
export function BubbleFormat({ editor }: Props) {
  if (!editor) return null;

  const setLink = () => {
    const prev = editor.getAttributes('link').href as string | undefined;
    const url = window.prompt('Link URL', prev ?? 'https://');
    if (url === null) return;
    const chain = editor.chain().focus().extendMarkRange('link');
    if (url.trim() === '') chain.unsetLink().run();
    else chain.setLink({ href: url.trim() }).run();
  };

  // Block transforms (turn the selected block into…).
  const blocks: Action[] = [
    {
      id: 'h1',
      icon: Heading1,
      title: 'Heading 1',
      isActive: () => editor.isActive('heading', { level: 1 }),
      run: () => editor.chain().focus().toggleHeading({ level: 1 }).run(),
    },
    {
      id: 'h2',
      icon: Heading2,
      title: 'Heading 2',
      isActive: () => editor.isActive('heading', { level: 2 }),
      run: () => editor.chain().focus().toggleHeading({ level: 2 }).run(),
    },
    {
      id: 'quote',
      icon: Quote,
      title: 'Quote',
      isActive: () => editor.isActive('blockquote'),
      run: () => editor.chain().focus().toggleBlockquote().run(),
    },
  ];

  // Inline marks.
  const marks: Action[] = [
    {
      id: 'bold',
      icon: Bold,
      title: 'Bold',
      isActive: () => editor.isActive('bold'),
      run: () => editor.chain().focus().toggleBold().run(),
    },
    {
      id: 'italic',
      icon: Italic,
      title: 'Italic',
      isActive: () => editor.isActive('italic'),
      run: () => editor.chain().focus().toggleItalic().run(),
    },
    {
      id: 'strike',
      icon: Strikethrough,
      title: 'Strikethrough',
      isActive: () => editor.isActive('strike'),
      run: () => editor.chain().focus().toggleStrike().run(),
    },
    {
      id: 'code',
      icon: Code,
      title: 'Inline code',
      isActive: () => editor.isActive('code'),
      run: () => editor.chain().focus().toggleCode().run(),
    },
    {
      id: 'highlight',
      icon: Highlighter,
      title: 'Highlight',
      isActive: () => editor.isActive('highlight'),
      run: () => editor.chain().focus().toggleHighlight().run(),
    },
  ];

  const link: Action = {
    id: 'link',
    icon: LinkIcon,
    title: 'Link',
    isActive: () => editor.isActive('link'),
    run: setLink,
  };

  return (
    <BubbleMenu
      editor={editor}
      tippyOptions={{ duration: 100, maxWidth: 'none' }}
      className="bb-pop flex items-center gap-0.5 rounded-lg border border-[var(--color-border)] bg-[var(--color-elevated)] p-1 shadow-xl"
    >
      {blocks.map((a) => (
        <Btn key={a.id} action={a} />
      ))}
      <Divider />
      {marks.map((a) => (
        <Btn key={a.id} action={a} />
      ))}
      <Divider />
      <Btn action={link} />
    </BubbleMenu>
  );
}

function Btn({ action }: { action: Action }) {
  return (
    <button
      title={action.title}
      onClick={action.run}
      className={cn(
        'rounded-md p-1.5',
        action.isActive()
          ? 'bg-[var(--color-accent-soft)] text-[var(--color-text)]'
          : 'text-[var(--color-muted)] hover:bg-[var(--color-surface)] hover:text-[var(--color-text)]'
      )}
    >
      <action.icon className="size-4" />
    </button>
  );
}

function Divider() {
  return <span className="mx-0.5 h-5 w-px bg-[var(--color-border)]" />;
}
