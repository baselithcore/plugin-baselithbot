import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { NodeLabel } from '@dbview/shared';
import { cn } from '../lib/cn.js';

export interface LabelNodeContext extends Record<string, unknown> {
  label: NodeLabel;
  highlighted?: boolean;
  onSelectLabel?: (labelId: string) => void;
  onSelectProperty?: (labelId: string, propertyName: string) => void;
}

type Props = NodeProps & { data: LabelNodeContext };

const PALETTE = [
  'border-l-violet-400',
  'border-l-cyan-400',
  'border-l-emerald-400',
  'border-l-amber-400',
  'border-l-blue-400',
];

function colorFor(label: string): string {
  let h = 0;
  for (const c of label) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return PALETTE[h % PALETTE.length] ?? PALETTE[0]!;
}

function LabelNodeImpl({ data }: Props) {
  const { label, highlighted, onSelectLabel, onSelectProperty } = data;
  const labelAccent = colorFor(label.label);
  return (
    <div
      className={cn(
        'rounded-lg overflow-hidden font-mono text-[11px] w-[220px] transition-shadow border-l-4',
        labelAccent,
      )}
      style={{
        background: 'rgb(var(--surface-1))',
        borderColor: highlighted ? 'rgb(var(--accent))' : 'rgb(var(--border))',
        borderWidth: 1,
        borderStyle: 'solid',
        ...(highlighted
          ? { boxShadow: '0 0 0 3px rgb(var(--accent) / 0.18), 0 10px 28px rgb(0 0 0 / 0.26)' }
          : { boxShadow: '0 4px 16px rgb(0 0 0 / 0.16)' }),
      }}
    >
      <Handle
        type="target"
        position={Position.Left}
        className="!bg-text-dim !border-none !w-1.5 !h-1.5"
      />
      <div
        className="dbview-drag-handle px-3 py-2.5 font-bold text-center text-[12px] cursor-grab active:cursor-grabbing select-none text-text"
        style={{
          background: 'rgb(var(--surface-2))',
          borderBottom: '1px solid rgb(var(--border))',
        }}
        onDoubleClick={(e) => {
          e.stopPropagation();
          onSelectLabel?.(label.id);
        }}
        title="Drag to move · Double-click to open details"
      >
        :{label.label}
      </div>
      {label.properties.length > 0 && (
        <div style={{ borderTop: '1px solid rgb(var(--border))' }}>
          {label.properties.slice(0, 8).map((p, i) => (
            <button
              key={p.name}
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onSelectProperty?.(label.id, p.name);
              }}
              className="w-full flex justify-between px-3 py-1 text-text hover:bg-surface-2 transition-colors text-left"
              style={{
                borderTop: i > 0 ? '1px solid rgb(var(--border) / 0.5)' : undefined,
              }}
            >
              <span>{p.name}</span>
              <span className="text-[9px] uppercase text-text-dim">{p.types[0] ?? 'ANY'}</span>
            </button>
          ))}
          {label.properties.length > 8 && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onSelectLabel?.(label.id);
              }}
              className="w-full px-3 py-1 text-[9px] text-text-dim text-center hover:bg-surface-2"
            >
              +{label.properties.length - 8} more
            </button>
          )}
        </div>
      )}
      <Handle
        type="source"
        position={Position.Right}
        className="!bg-text-dim !border-none !w-1.5 !h-1.5"
      />
    </div>
  );
}

export const LabelNode = memo(LabelNodeImpl);
