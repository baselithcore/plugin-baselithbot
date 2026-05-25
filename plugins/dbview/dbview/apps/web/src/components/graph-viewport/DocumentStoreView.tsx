import { Database } from 'lucide-react';
import { EmptyState } from '../ui/EmptyState.js';
import { cn } from '../../lib/cn.js';

interface DocumentStoreViewProps {
  schema: {
    database: string;
    collections: Array<{
      id: string;
      name: string;
      docCount?: number;
      sizeBytes?: number;
      indexes: string[];
      fields: Array<{ name: string; types: string[]; presence?: number }>;
    }>;
  };
  matched?: Set<string>;
  onSelectCollection: (id: string) => void;
}

export function DocumentStoreView({ schema, matched, onSelectCollection }: DocumentStoreViewProps) {
  if (schema.collections.length === 0) {
    return (
      <EmptyState
        icon={<Database className="w-5 h-5" />}
        title="No collections"
        description={`Database ${schema.database} is empty.`}
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
                <span className="chip text-[9px] uppercase shrink-0">mongodb</span>
              </div>
              <div className="grid grid-cols-2 gap-2 mb-3 text-[11px] font-mono">
                <div className="flex flex-col gap-0.5">
                  <span className="text-text-dim text-[9px] uppercase">Docs</span>
                  <span className="text-text">
                    {typeof c.docCount === 'number' ? c.docCount.toLocaleString() : '—'}
                  </span>
                </div>
                <div className="flex flex-col gap-0.5">
                  <span className="text-text-dim text-[9px] uppercase">Size</span>
                  <span className="text-text">
                    {typeof c.sizeBytes === 'number'
                      ? `${(c.sizeBytes / 1024).toFixed(0)} KB`
                      : '—'}
                  </span>
                </div>
              </div>
              {c.indexes.length > 0 && (
                <div className="mb-3">
                  <div className="text-text-dim text-[9px] uppercase mb-1">Indexes</div>
                  <div className="flex flex-wrap gap-1">
                    {c.indexes.map((i) => (
                      <span key={i} className="chip text-[10px]">
                        {i}
                      </span>
                    ))}
                  </div>
                </div>
              )}
              <div>
                <div className="text-text-dim text-[9px] uppercase mb-1">
                  Fields ({c.fields.length})
                </div>
                <div className="flex flex-wrap gap-1">
                  {c.fields.slice(0, 10).map((f) => (
                    <span
                      key={f.name}
                      className="text-[10px] font-mono px-1.5 py-0.5 rounded truncate max-w-[180px]"
                      style={{
                        background: 'rgb(var(--surface-2))',
                        color: 'rgb(var(--text-muted))',
                      }}
                      title={`${f.name}: ${f.types.join('|')}`}
                    >
                      {f.name}
                    </span>
                  ))}
                  {c.fields.length > 10 && (
                    <span className="text-[10px] text-text-dim">+{c.fields.length - 10}</span>
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
