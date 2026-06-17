import { useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { ChevronRight, FileText, Plus, Trash2 } from 'lucide-react';
import type { TreeNode } from '@/lib/types';
import { cn } from '@/lib/cn';

interface Props {
  node: TreeNode;
  depth: number;
  activeId: string | null;
  collapsed: Set<string>;
  dropId: string | null;
  onToggle: (id: string) => void;
  onOpen: (id: string) => void;
  onAddChild: (parentId: string) => void;
  onDelete: (id: string, title: string) => void;
  onDragStart: (id: string) => void;
  onDropOn: (targetId: string | null) => void;
  onDragOverId: (id: string | null) => void;
}

/** One row of the page tree, recursive over its children. */
export function TreeRow(props: Props) {
  const { node, depth, activeId, collapsed, dropId } = props;
  const [hover, setHover] = useState(false);
  const hasKids = node.children.length > 0;
  const open = !collapsed.has(node.id);
  const isDrop = dropId === node.id;
  const isActive = node.id === activeId;

  return (
    <div>
      <div
        draggable
        onDragStart={(e) => {
          e.stopPropagation();
          props.onDragStart(node.id);
        }}
        onDragOver={(e) => {
          e.preventDefault();
          props.onDragOverId(node.id);
        }}
        onDragLeave={() => props.onDragOverId(null)}
        onDrop={(e) => {
          e.preventDefault();
          e.stopPropagation();
          props.onDropOn(node.id);
        }}
        onMouseEnter={() => setHover(true)}
        onMouseLeave={() => setHover(false)}
        onClick={() => props.onOpen(node.id)}
        style={{ paddingLeft: depth * 12 + 4 }}
        className={cn(
          'group relative flex cursor-pointer items-center gap-1 rounded-lg py-1.5 pr-1 text-sm transition-colors',
          isActive
            ? 'bg-[var(--color-accent-soft)] text-[var(--color-text)]'
            : 'text-[var(--color-muted)] hover:bg-[var(--color-elevated)]/70',
          isDrop && 'ring-1 ring-[var(--color-accent)]'
        )}
      >
        {isActive && (
          <motion.span
            layoutId="tree-active"
            className="bb-gradient absolute left-0 top-1/2 h-4 w-[3px] -translate-y-1/2 rounded-full"
            transition={{ type: 'spring', stiffness: 500, damping: 36 }}
          />
        )}
        <button
          onClick={(e) => {
            e.stopPropagation();
            if (hasKids) props.onToggle(node.id);
          }}
          className={cn('shrink-0 rounded p-0.5', !hasKids && 'invisible')}
          title={open ? 'Collapse' : 'Expand'}
        >
          <ChevronRight
            className={cn('size-3.5 transition-transform duration-200', open && 'rotate-90')}
          />
        </button>
        <FileText className="size-3.5 shrink-0 opacity-70" />
        <span className="truncate">{node.title}</span>
        {hover && (
          <span className="ml-auto flex items-center gap-0.5">
            <button
              title="New child note"
              onClick={(e) => {
                e.stopPropagation();
                props.onAddChild(node.id);
              }}
              className="rounded p-0.5 text-[var(--color-faint)] hover:text-[var(--color-accent)]"
            >
              <Plus className="size-3.5" />
            </button>
            <button
              title="Delete"
              onClick={(e) => {
                e.stopPropagation();
                props.onDelete(node.id, node.title);
              }}
              className="rounded p-0.5 text-[var(--color-faint)] hover:text-[var(--color-danger)]"
            >
              <Trash2 className="size-3.5" />
            </button>
          </span>
        )}
      </div>
      <AnimatePresence initial={false}>
        {open && hasKids && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: [0.22, 1, 0.36, 1] }}
            className="overflow-hidden"
          >
            {node.children.map((child) => (
              <TreeRow key={child.id} {...props} node={child} depth={depth + 1} />
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
