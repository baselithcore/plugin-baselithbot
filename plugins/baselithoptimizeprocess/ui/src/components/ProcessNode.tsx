import { Handle, Position } from '@xyflow/react';
import type { LucideIcon } from 'lucide-react';
import { Flag, GitFork, Play, Rows3, Square } from 'lucide-react';
import { memo } from 'react';

import type { NodeKind, Severity } from '../api/types';

interface ProcessNodeData {
  label: string;
  kind: NodeKind;
  severity?: Severity;
}

const KIND_ICON: Record<NodeKind, LucideIcon> = {
  start: Play,
  task: Square,
  decision: GitFork,
  parallel: Rows3,
  end: Flag,
};

/** Custom React Flow node: glassy card tinted by its worst bottleneck. */
function ProcessNodeImpl({ data }: { data: ProcessNodeData }) {
  const Icon = KIND_ICON[data.kind];
  return (
    <div
      className="min-w-[176px] max-w-[244px] rounded-xl border bg-ink-850/95 px-3.5 py-2.5 backdrop-blur-md transition-shadow"
      style={{
        borderColor: 'color-mix(in srgb, var(--node-accent) 55%, transparent)',
        boxShadow:
          '0 0 0 1px color-mix(in srgb, var(--node-accent) 25%, transparent), 0 14px 32px -16px var(--node-accent)',
      }}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!h-2 !w-2 !border-0 !bg-slate-500"
      />
      <div className="flex items-center gap-2">
        <span
          className="grid h-6 w-6 shrink-0 place-items-center rounded-md"
          style={{
            backgroundColor: 'color-mix(in srgb, var(--node-accent) 16%, transparent)',
            color: 'var(--node-accent)',
          }}
          aria-hidden="true"
        >
          <Icon size={13} strokeWidth={2.2} />
        </span>
        <span className="truncate text-sm font-semibold text-slate-100">{data.label}</span>
      </div>
      <div className="mt-1 flex items-center justify-between pl-8">
        <span className="text-[10px] uppercase tracking-wide text-slate-500">{data.kind}</span>
        {data.severity && (
          <span
            className="text-[10px] font-semibold uppercase"
            style={{ color: 'var(--node-accent)' }}
          >
            {data.severity}
          </span>
        )}
      </div>
      <Handle
        type="source"
        position={Position.Right}
        className="!h-2 !w-2 !border-0 !bg-slate-500"
      />
    </div>
  );
}

export const ProcessNode = memo(ProcessNodeImpl);
