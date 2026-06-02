import { Icon } from '../../Icon';
import type { SuggestionGroup } from '../types';

export function EmptyChat({
  disabled,
  suggestions,
  onPick,
}: {
  disabled: boolean;
  suggestions: SuggestionGroup[];
  onPick: (s: string) => void;
}) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 px-4 py-6">
      <div className="grid h-10 w-10 place-items-center rounded-lg border border-bg-line bg-bg-overlay text-brand">
        <Icon.Sparkles size={16} />
      </div>
      <p className="text-center text-xs text-text-muted">
        {disabled ? 'Carica un grafo per chattare.' : 'Comincia con una domanda:'}
      </p>
      {!disabled && (
        <div className="flex w-full max-w-md flex-col gap-2.5">
          {suggestions.map((g) => (
            <div key={g.group}>
              <p className="mb-1 text-2xs font-mono uppercase tracking-wider text-text-muted">
                {g.group}
              </p>
              <ul className="flex flex-col gap-1">
                {g.items.map((s) => (
                  <li key={s}>
                    <button
                      type="button"
                      onClick={() => onPick(s)}
                      className="w-full rounded-md border border-bg-line bg-bg-overlay px-3 py-2 text-left font-body text-xs text-text-secondary transition-colors hover:border-brand/40 hover:bg-bg-hover/70 hover:text-text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-brand/40"
                    >
                      {s}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
