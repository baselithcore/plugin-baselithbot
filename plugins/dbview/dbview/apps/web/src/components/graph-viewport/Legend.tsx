import { ArrowRight, Circle, Database, Key, Link2 } from 'lucide-react';
import type { UnifiedSchema } from '@dbview/shared';

function LegendItem({ icon, label }: { icon: React.ReactNode; label: string }) {
  return (
    <div className="flex items-center gap-2 text-text-muted">
      <span className="w-3 h-3 inline-flex items-center justify-center shrink-0">{icon}</span>
      <span>{label}</span>
    </div>
  );
}

export function Legend({ kind }: { kind: UnifiedSchema['kind'] }) {
  return (
    <div className="absolute top-2 right-2 z-10 toolbar-surface px-2.5 py-2 text-[10px] flex flex-col gap-1.5">
      {kind === 'relational' ? (
        <>
          <LegendItem icon={<Database className="w-3 h-3 text-text-muted" />} label="table" />
          <LegendItem
            icon={<Key className="w-3 h-3 text-amber-400" strokeWidth={2.5} />}
            label="primary key"
          />
          <LegendItem
            icon={<Link2 className="w-3 h-3 text-sky-400" strokeWidth={2.5} />}
            label="foreign key"
          />
          <LegendItem
            icon={
              <span className="w-3 inline-flex justify-center text-rose-400 font-bold leading-none">
                *
              </span>
            }
            label="not null"
          />
          <LegendItem
            icon={<ArrowRight className="w-3 h-3 text-sky-300" />}
            label="foreign-key target"
          />
        </>
      ) : kind === 'graph' ? (
        <>
          <LegendItem
            icon={<Circle className="w-3 h-3 fill-fuchsia-500 text-fuchsia-500" />}
            label="node label"
          />
          <LegendItem
            icon={<span className="text-[9px] font-mono text-indigo-400 leading-none">→</span>}
            label="relationship"
          />
        </>
      ) : (
        <>
          <LegendItem
            icon={<Database className="w-3 h-3 text-rose-400" strokeWidth={2.5} />}
            label="collection"
          />
          <LegendItem
            icon={<span className="text-[9px] font-mono text-amber-400 leading-none">d</span>}
            label="vector size"
          />
        </>
      )}
    </div>
  );
}
