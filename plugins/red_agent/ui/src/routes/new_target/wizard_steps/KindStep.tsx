import { type TargetKind } from '../../../lib/api';
import { Card, Icon } from '../../../components/ui';
import { KIND_META, KIND_ORDER } from '../../../lib/targets';
import { KindIcon } from './_shared';

export function KindStep({
  kind,
  setKind,
}: {
  kind: TargetKind | null;
  setKind: (k: TargetKind) => void;
}) {
  return (
    <Card title="What kind of target?" subtitle="Pick the entity you want to assess">
      <div className="grid gap-3 sm:grid-cols-2">
        {KIND_ORDER.map((k) => {
          const meta = KIND_META[k];
          const sel = kind === k;
          const disabled = !!meta.comingSoon;
          return (
            <button
              key={k}
              type="button"
              disabled={disabled}
              onClick={() => !disabled && setKind(k)}
              className={`relative flex items-start gap-3 rounded-lg border bg-gradient-to-br p-4 text-left transition-all ${
                sel
                  ? 'border-brand/60 ring-1 ring-brand/40'
                  : disabled
                    ? 'border-bg-line opacity-60 cursor-not-allowed'
                    : 'border-bg-line hover:border-bg-line-strong'
              } ${meta.accent}`}
            >
              <div className="grid h-10 w-10 place-items-center rounded-md bg-bg-elevated/80 ring-1 ring-current/20">
                <KindIcon k={k} size={18} />
              </div>
              <div className="min-w-0 flex-1">
                <div className="font-display text-sm font-medium text-text-primary">
                  {meta.label}
                </div>
                <p className="mt-1 text-xs text-text-muted">{meta.description}</p>
                <p className="mt-2 font-mono text-2xs text-text-subtle">{meta.hint}</p>
              </div>
              {meta.comingSoon && (
                <span className="absolute right-3 top-3 rounded bg-amber-500/10 px-1.5 py-0.5 text-2xs font-mono uppercase tracking-wider text-amber-300 ring-1 ring-amber-500/20">
                  coming soon
                </span>
              )}
              {sel && (
                <span className="absolute right-3 top-3 grid h-5 w-5 place-items-center rounded-full bg-brand/20 text-brand ring-1 ring-brand/40">
                  <Icon.Check size={11} />
                </span>
              )}
            </button>
          );
        })}
      </div>
    </Card>
  );
}
