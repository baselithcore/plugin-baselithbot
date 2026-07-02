import { Database } from 'lucide-react';
import { EmptyState } from '../ui/EmptyState.js';
import { cn } from '../../lib/cn.js';

interface VectorStoreViewProps {
  schema: {
    collections: Array<{
      id: string;
      name: string;
      vectorSize: number;
      distance: string;
      pointCount?: number;
      namedVectors?: Array<{ name: string; size: number }>;
      payloadFields: Array<{ name: string; types: string[]; sampleValues?: string[] }>;
    }>;
  };
  matched?: Set<string>;
  onSelectCollection: (id: string) => void;
}

export function VectorStoreView({ schema, matched, onSelectCollection }: VectorStoreViewProps) {
  if (schema.collections.length === 0) {
    return (
      <EmptyState
        icon={<Database className="w-5 h-5" />}
        title="No collections"
        description="This Qdrant instance has no collections yet."
      />
    );
  }
  return (
    <div className="absolute inset-0 overflow-auto pt-20 px-6 pb-6">
      <div className="grid gap-3 grid-cols-[repeat(auto-fill,minmax(320px,1fr))] max-w-[1400px] mx-auto">
        {schema.collections.map((c) => {
          const isMatched = matched ? matched.has(c.id) : true;
          return (
            <button
              key={c.id}
              type="button"
              onClick={() => onSelectCollection(c.id)}
              className={cn(
                'panel-glass text-left p-4 transition-all hover:ring-1 hover:ring-accent/40',
                !isMatched && 'opacity-30'
              )}
              style={{ minHeight: 180 }}
            >
              <div className="flex items-start justify-between gap-2 mb-3">
                <div className="font-mono text-[13px] font-semibold truncate">{c.name}</div>
                <span className="chip text-[9px] uppercase shrink-0">qdrant</span>
              </div>
              <div className="grid grid-cols-2 gap-2 mb-3 text-[11px] font-mono">
                <div className="flex flex-col gap-0.5">
                  <span className="text-text-dim text-[9px] uppercase">Vector</span>
                  <span className="text-text">
                    {c.vectorSize > 0 ? `${c.vectorSize}d` : '—'}
                    <span className="text-text-dim ml-1">{c.distance}</span>
                  </span>
                </div>
                <div className="flex flex-col gap-0.5">
                  <span className="text-text-dim text-[9px] uppercase">Points</span>
                  <span className="text-text">
                    {typeof c.pointCount === 'number' ? c.pointCount.toLocaleString() : '—'}
                  </span>
                </div>
              </div>
              {c.namedVectors && c.namedVectors.length > 0 && (
                <div className="mb-3">
                  <div className="text-text-dim text-[9px] uppercase mb-1">Named vectors</div>
                  <div className="flex flex-wrap gap-1">
                    {c.namedVectors.map((nv) => (
                      <span key={nv.name} className="chip text-[10px]">
                        {nv.name} · {nv.size}d
                      </span>
                    ))}
                  </div>
                </div>
              )}
              <div>
                <div className="text-text-dim text-[9px] uppercase mb-1">
                  Payload ({c.payloadFields.length})
                </div>
                <div className="flex flex-wrap gap-1">
                  {c.payloadFields.slice(0, 8).map((p) => (
                    <span
                      key={p.name}
                      className="text-[10px] font-mono px-1.5 py-0.5 rounded"
                      style={{
                        background: 'rgb(var(--surface-2))',
                        color: 'rgb(var(--text-muted))',
                      }}
                      title={p.types.join('|')}
                    >
                      {p.name}
                    </span>
                  ))}
                  {c.payloadFields.length > 8 && (
                    <span className="text-[10px] text-text-dim">+{c.payloadFields.length - 8}</span>
                  )}
                </div>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
