import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import { ArrowRight, Database, Hash, Key, Link2 } from 'lucide-react';
import type { TableNode as TableNodeData } from '@dbview/shared';
import { cn } from '../lib/cn.js';

export interface FkTarget {
  tableName: string;
  columnName: string;
}

export interface TableNodeContext extends Record<string, unknown> {
  table: TableNodeData;
  highlighted?: boolean;
  dimmed?: boolean;
  fkTargets?: Record<string, FkTarget>;
  onSelectTable?: (tableId: string) => void;
  onSelectColumn?: (tableId: string, columnName: string) => void;
}

type Props = NodeProps & { data: TableNodeContext };

const HEADER_PALETTE = [
  { bar: 'border-l-teal-400', accent: 'text-teal-300' },
  { bar: 'border-l-sky-400', accent: 'text-sky-300' },
  { bar: 'border-l-amber-400', accent: 'text-amber-300' },
  { bar: 'border-l-rose-400', accent: 'text-rose-300' },
  { bar: 'border-l-violet-400', accent: 'text-violet-300' },
  { bar: 'border-l-emerald-400', accent: 'text-emerald-300' },
];

function colorForSchema(schema: string): (typeof HEADER_PALETTE)[number] {
  let h = 0;
  for (const c of schema) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return HEADER_PALETTE[h % HEADER_PALETTE.length] ?? HEADER_PALETTE[0]!;
}

function formatRowCount(n: number): string {
  if (n < 1000) return String(n);
  if (n < 1_000_000) return `${(n / 1000).toFixed(n < 10_000 ? 1 : 0)}k`;
  return `${(n / 1_000_000).toFixed(n < 10_000_000 ? 1 : 0)}M`;
}

function TableNodeImpl({ data, selected }: Props) {
  const { table, highlighted, dimmed, fkTargets, onSelectTable, onSelectColumn } = data;
  const schemaColor = colorForSchema(table.schema);
  const isActive = highlighted || selected;

  return (
    <div
      className={cn(
        'group/node rounded-lg overflow-hidden font-mono text-[11px] w-[280px] border-l-4',
        'transition-[box-shadow,transform] duration-150 ease-[cubic-bezier(0.25,1,0.5,1)]',
        !isActive && !dimmed && 'hover:-translate-y-[1px]',
        schemaColor.bar,
        dimmed && 'opacity-30 grayscale-[0.4]',
      )}
      style={{
        background: 'rgb(var(--surface-1))',
        borderColor: isActive ? 'rgb(var(--accent))' : 'rgb(var(--border))',
        borderWidth: 1,
        borderStyle: 'solid',
        boxShadow: isActive
          ? '0 0 0 3px rgb(var(--accent) / 0.22), 0 14px 32px rgb(0 0 0 / 0.32)'
          : '0 4px 14px rgb(0 0 0 / 0.18)',
      }}
      role="group"
      aria-label={`Table ${table.schema}.${table.name}`}
    >
      <button
        type="button"
        className={cn(
          'dbview-drag-handle w-full px-3 py-2 flex justify-between items-center',
          'cursor-grab active:cursor-grabbing select-none text-left',
          'transition-colors',
        )}
        style={{
          background: isActive ? 'rgb(var(--accent) / 0.10)' : 'rgb(var(--surface-2))',
          borderBottom: '1px solid rgb(var(--border))',
        }}
        onClick={(e) => {
          e.stopPropagation();
          onSelectTable?.(table.id);
        }}
        title="Click to open · Drag to move"
      >
        <span
          className={cn(
            'text-[12px] font-semibold truncate flex items-center gap-1.5',
            isActive ? 'text-text' : 'text-text',
          )}
        >
          <Database className={cn('w-3.5 h-3.5', schemaColor.accent)} />
          {table.name}
        </span>
        <span className="flex items-center gap-1.5 shrink-0">
          {typeof table.rowCountEstimate === 'number' && (
            <span
              className="inline-flex items-center gap-0.5 text-[9px] font-mono text-text-dim"
              title={`~${table.rowCountEstimate.toLocaleString()} rows`}
            >
              <Hash className="w-2.5 h-2.5" />
              {formatRowCount(table.rowCountEstimate)}
            </span>
          )}
          <span className="text-[9px] uppercase tracking-wider px-1.5 h-4 inline-flex items-center rounded text-text-dim border border-border-subtle">
            {table.schema}
          </span>
        </span>
      </button>

      <div>
        {table.columns.map((col, i) => {
          const fkTarget = col.isForeignKey ? fkTargets?.[col.name] : undefined;
          return (
            <button
              key={col.name}
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onSelectColumn?.(table.id, col.name);
              }}
              className={cn(
                'relative w-full grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 px-3 py-1.5',
                'transition-colors text-left cursor-pointer',
                'hover:bg-[rgb(var(--surface-2))]',
                'focus-visible:bg-[rgb(var(--surface-2))]',
              )}
              style={{
                borderTop: i > 0 ? '1px solid rgb(var(--border) / 0.45)' : undefined,
              }}
              aria-label={`Column ${col.name} ${col.dataType}${!col.nullable ? ' not null' : ''}`}
            >
              <Handle
                type="target"
                position={Position.Left}
                id={`col-${col.name}`}
                className="!bg-text-dim !border-none !w-1.5 !h-1.5"
              />
              <div className="flex items-center gap-1.5 text-text min-w-0">
                {col.isPrimaryKey ? (
                  <Key className="w-3 h-3 text-amber-400 shrink-0" strokeWidth={2.5} />
                ) : col.isForeignKey ? (
                  <Link2 className="w-3 h-3 text-sky-400 shrink-0" strokeWidth={2.5} />
                ) : (
                  <span className="w-3 h-3 inline-block shrink-0" />
                )}
                <span
                  className={cn(
                    'truncate',
                    col.isPrimaryKey && 'font-semibold text-text',
                    !col.isPrimaryKey && 'text-text-muted',
                  )}
                >
                  {col.name}
                </span>
                {fkTarget && (
                  <span className="hidden group-hover/node:inline-flex items-center gap-0.5 text-[9px] text-sky-300/80 truncate ml-1">
                    <ArrowRight className="w-2.5 h-2.5" />
                    {fkTarget.tableName}.{fkTarget.columnName}
                  </span>
                )}
              </div>
              <span className="flex items-center gap-1 text-[9px] uppercase tracking-wider text-text-dim max-w-[110px]">
                <span className="truncate">{col.dataType}</span>
                {!col.nullable && (
                  <span className="text-rose-400 font-bold" title="not null" aria-label="not null">
                    *
                  </span>
                )}
              </span>
              <Handle
                type="source"
                position={Position.Right}
                id={`col-${col.name}`}
                className="!bg-text-dim !border-none !w-1.5 !h-1.5"
              />
            </button>
          );
        })}
      </div>
    </div>
  );
}

export const TableNode = memo(TableNodeImpl);
