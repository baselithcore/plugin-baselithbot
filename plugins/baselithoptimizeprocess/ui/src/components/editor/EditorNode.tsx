import { Handle, Position, type NodeProps } from '@xyflow/react';
import { memo } from 'react';

import type { NodeKind } from '../../api/types';
import type { FlowNode } from './useProcessEditor';

const KIND_GLYPH: Record<NodeKind, string> = {
  start: '▶',
  task: '■',
  decision: '◆',
  parallel: '⫼',
  end: '⏹',
};

const KIND_ACCENT: Record<NodeKind, string> = {
  start: '#34d399',
  task: '#38bdf8',
  decision: '#fbbf24',
  parallel: '#a78bfa',
  end: '#f43f5e',
};

/** Editable canvas node with connect handles, tinted by step kind. */
function EditorNodeImpl({ data, selected }: NodeProps<FlowNode>) {
  const accent = KIND_ACCENT[data.kind];
  return (
    <div
      className="min-w-[150px] rounded-xl border bg-ink-850/95 px-3.5 py-2.5 backdrop-blur-md transition-all"
      style={{
        borderColor: selected ? accent : `color-mix(in srgb, ${accent} 45%, transparent)`,
        boxShadow: selected
          ? `0 0 0 2px ${accent}, 0 14px 32px -14px ${accent}`
          : `0 0 0 1px color-mix(in srgb, ${accent} 22%, transparent)`,
      }}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!h-2.5 !w-2.5 !border-2 !border-ink-950"
        style={{ background: accent }}
      />
      <div className="flex items-center gap-2">
        <span className="text-xs" style={{ color: accent }} aria-hidden>
          {KIND_GLYPH[data.kind]}
        </span>
        <span className="text-sm font-semibold text-slate-100">{data.label || 'Untitled'}</span>
      </div>
      <div className="mt-0.5 flex items-center justify-between gap-2">
        <span className="text-[10px] uppercase tracking-wide text-slate-500">{data.kind}</span>
        {data.role && <span className="truncate text-[10px] text-slate-400">{data.role}</span>}
      </div>
      <Handle
        type="source"
        position={Position.Right}
        className="!h-2.5 !w-2.5 !border-2 !border-ink-950"
        style={{ background: accent }}
      />
    </div>
  );
}

export const EditorNode = memo(EditorNodeImpl);
