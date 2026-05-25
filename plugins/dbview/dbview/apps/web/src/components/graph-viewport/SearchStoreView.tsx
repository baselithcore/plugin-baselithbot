import { Database } from 'lucide-react';
import { EmptyState } from '../ui/EmptyState.js';
import { cn } from '../../lib/cn.js';

interface SearchStoreViewProps {
  schema: {
    cluster?: string;
    indices: Array<{
      id: string;
      name: string;
      docCount?: number;
      sizeBytes?: number;
      aliases: string[];
      fields: Array<{ name: string; type: string; analyzed?: boolean }>;
    }>;
  };
  matched?: Set<string>;
  onSelectIndex: (id: string) => void;
}

export function SearchStoreView({ schema, matched, onSelectIndex }: SearchStoreViewProps) {
  if (schema.indices.length === 0) {
    return (
      <EmptyState
        icon={<Database className="w-5 h-5" />}
        title="No indices"
        description={
          schema.cluster
            ? `Cluster ${schema.cluster} has no user indices.`
            : 'No user indices found.'
        }
      />
    );
  }
  return (
    <div className="absolute inset-0 overflow-auto pt-20 px-6 pb-6">
      <div className="grid gap-3 grid-cols-[repeat(auto-fill,minmax(320px,1fr))] max-w-[1400px] mx-auto">
        {schema.indices.map((idx) => {
          const isMatched = matched ? matched.has(idx.id) : true;
          return (
            <button
              key={idx.id}
              type="button"
              onClick={() => onSelectIndex(idx.id)}
              className={cn(
                'panel-glass text-left p-4 transition-all hover:ring-1 hover:ring-accent/40',
                !isMatched && 'opacity-30'
              )}
              style={{ minHeight: 180 }}
            >
              <div className="flex items-start justify-between gap-2 mb-3">
                <div className="font-mono text-[13px] font-semibold truncate">{idx.name}</div>
                <span className="chip text-[9px] uppercase shrink-0">elasticsearch</span>
              </div>
              <div className="grid grid-cols-2 gap-2 mb-3 text-[11px] font-mono">
                <div className="flex flex-col gap-0.5">
                  <span className="text-text-dim text-[9px] uppercase">Docs</span>
                  <span className="text-text">
                    {typeof idx.docCount === 'number' ? idx.docCount.toLocaleString() : '—'}
                  </span>
                </div>
                <div className="flex flex-col gap-0.5">
                  <span className="text-text-dim text-[9px] uppercase">Size</span>
                  <span className="text-text">
                    {typeof idx.sizeBytes === 'number'
                      ? `${(idx.sizeBytes / 1024).toFixed(0)} KB`
                      : '—'}
                  </span>
                </div>
              </div>
              {idx.aliases.length > 0 && (
                <div className="mb-3">
                  <div className="text-text-dim text-[9px] uppercase mb-1">Aliases</div>
                  <div className="flex flex-wrap gap-1">
                    {idx.aliases.map((a) => (
                      <span key={a} className="chip text-[10px]">
                        {a}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              <div>
                <div className="text-text-dim text-[9px] uppercase mb-1">
                  Fields ({idx.fields.length})
                </div>
                <div className="flex flex-wrap gap-1">
                  {idx.fields.slice(0, 10).map((f) => (
                    <span
                      key={f.name}
                      className="text-[10px] font-mono px-1.5 py-0.5 rounded truncate max-w-[180px]"
                      style={{
                        background: 'rgb(var(--surface-2))',
                        color: 'rgb(var(--text-muted))',
                      }}
                      title={`${f.name}: ${f.type}`}
                    >
                      {f.name}
                    </span>
                  ))}
                  {idx.fields.length > 10 && (
                    <span className="text-[10px] text-text-dim">+{idx.fields.length - 10}</span>
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
