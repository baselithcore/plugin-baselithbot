import { Database } from 'lucide-react';
import { EmptyState } from '../ui/EmptyState.js';
import { cn } from '../../lib/cn.js';

interface KeyValueStoreViewProps {
  schema: {
    db: number;
    totalKeys: number;
    namespaces: Array<{
      pattern: string;
      types: string[];
      sampleKeys: string[];
      keyCount: number;
    }>;
  };
  matched?: Set<string>;
  onSelectNamespace: (id: string) => void;
}

export function KeyValueStoreView({ schema, matched, onSelectNamespace }: KeyValueStoreViewProps) {
  if (schema.namespaces.length === 0) {
    return (
      <EmptyState
        icon={<Database className="w-5 h-5" />}
        title="No keys"
        description={`Redis DB ${schema.db} is empty.`}
      />
    );
  }
  return (
    <div className="absolute inset-0 overflow-auto pt-20 px-6 pb-6">
      <div className="grid gap-3 grid-cols-[repeat(auto-fill,minmax(320px,1fr))] max-w-[1400px] mx-auto">
        {schema.namespaces.map((n) => {
          const isMatched = matched ? matched.has(n.pattern) : true;
          return (
            <button
              key={n.pattern}
              type="button"
              onClick={() => onSelectNamespace(n.pattern)}
              className={cn(
                'panel-glass text-left p-4 transition-all hover:ring-1 hover:ring-accent/40',
                !isMatched && 'opacity-30',
              )}
              style={{ minHeight: 160 }}
            >
              <div className="flex items-start justify-between gap-2 mb-3">
                <div className="font-mono text-[13px] font-semibold truncate">{n.pattern}</div>
                <span className="chip text-[9px] uppercase shrink-0">redis</span>
              </div>
              <div className="grid grid-cols-2 gap-2 mb-3 text-[11px] font-mono">
                <div className="flex flex-col gap-0.5">
                  <span className="text-text-dim text-[9px] uppercase">Keys</span>
                  <span className="text-text">{n.keyCount.toLocaleString()}</span>
                </div>
                <div className="flex flex-col gap-0.5">
                  <span className="text-text-dim text-[9px] uppercase">Types</span>
                  <span className="text-text">{n.types.join(', ') || '—'}</span>
                </div>
              </div>
              {n.sampleKeys.length > 0 && (
                <div>
                  <div className="text-text-dim text-[9px] uppercase mb-1">Samples</div>
                  <div className="flex flex-wrap gap-1">
                    {n.sampleKeys.slice(0, 6).map((k) => (
                      <span
                        key={k}
                        className="text-[10px] font-mono px-1.5 py-0.5 rounded truncate max-w-[180px]"
                        style={{
                          background: 'rgb(var(--surface-2))',
                          color: 'rgb(var(--text-muted))',
                        }}
                        title={k}
                      >
                        {k}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
