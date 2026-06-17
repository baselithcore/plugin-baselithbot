import type { AgentBlueprint } from '../lib/types';

interface BlueprintCardProps {
  blueprint: AgentBlueprint;
  onDelete?: (id: string) => void;
  onSelect?: (b: AgentBlueprint) => void;
  active?: boolean;
}

const PROVIDER_TINT: Record<string, string> = {
  anthropic: 'text-amber-300 border-amber-300/30',
  openai: 'text-emerald-300 border-emerald-300/30',
  ollama: 'text-cyan border-cyan/30',
};

/** Compact summary of a synthesised agent blueprint. */
export function BlueprintCard({ blueprint, onDelete, onSelect, active }: BlueprintCardProps) {
  const tint = PROVIDER_TINT[blueprint.provider] ?? 'text-slate-300 border-slate-500/30';
  return (
    <div
      onClick={() => onSelect?.(blueprint)}
      className={[
        'rounded-xl border p-4 transition-colors',
        onSelect ? 'cursor-pointer' : '',
        active
          ? 'border-iris/50 bg-iris/10 shadow-glow'
          : 'border-ink-600/60 bg-ink-800/40 hover:border-iris/30',
      ].join(' ')}
    >
      <div className="flex items-center justify-between gap-3">
        <h3 className="truncate text-sm font-semibold text-slate-100">{blueprint.name}</h3>
        <span className={`shrink-0 rounded-md border px-2 py-0.5 text-[11px] font-medium ${tint}`}>
          {blueprint.provider}
        </span>
      </div>
      <p className="mt-1 line-clamp-2 text-xs text-slate-400">{blueprint.description}</p>
      <div className="mt-3 flex flex-wrap gap-1.5">
        {blueprint.scope.capabilities.map((cap) => (
          <span
            key={cap}
            className="rounded bg-ink-700/70 px-1.5 py-0.5 font-mono text-[10px] text-slate-300"
          >
            {cap}
          </span>
        ))}
      </div>
      <div className="mt-3 flex items-center justify-between text-[11px] text-slate-500">
        <span className="font-mono">{blueprint.id}</span>
        {onDelete && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete(blueprint.id);
            }}
            className="text-rose-400/80 hover:text-rose-300"
          >
            delete
          </button>
        )}
      </div>
    </div>
  );
}
