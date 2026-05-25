import { DIALECT_META, SUPPORTED_DIALECTS, type Dialect } from '@dbview/shared';
import { cn } from '../../lib/cn.js';
import { DialectIcon } from './DialectIcon.js';

interface Props {
  value: Dialect;
  onChange: (d: Dialect) => void;
}

export function DialectGrid({ value, onChange }: Props) {
  return (
    <div className="grid grid-cols-4 gap-1.5" role="radiogroup" aria-label="Database type">
      {SUPPORTED_DIALECTS.map((d) => {
        const meta = DIALECT_META[d];
        const active = value === d;
        return (
          <button
            key={d}
            type="button"
            role="radio"
            aria-checked={active}
            onClick={() => onChange(d)}
            className={cn(
              'flex flex-col items-center gap-1.5 py-2.5 px-1 rounded-lg text-[10px] font-medium transition-all border relative',
              active ? 'ring-1 ring-accent/45 shadow-sm' : 'hover:bg-surface-3',
              !meta.available && 'opacity-65'
            )}
            style={{
              background: active
                ? 'linear-gradient(135deg, rgb(var(--accent) / 0.16), rgb(var(--brand) / 0.08))'
                : 'rgb(var(--surface-2) / 0.78)',
              color: active ? 'rgb(var(--accent))' : 'rgb(var(--text-muted))',
              borderColor: active ? 'rgb(var(--accent) / 0.5)' : 'rgb(var(--border-subtle))',
            }}
            title={
              meta.available
                ? meta.beta
                  ? `${meta.label} (beta)`
                  : meta.label
                : `${meta.label} (coming soon)`
            }
          >
            <DialectIcon dialect={d} size={26} />
            <span className="leading-tight text-center">{meta.label}</span>
            {!meta.available ? (
              <span
                className="absolute top-1 right-1 text-[8px] px-1 rounded uppercase tracking-wider"
                style={{
                  background: 'rgb(var(--surface-3))',
                  color: 'rgb(var(--text-dim))',
                }}
              >
                Soon
              </span>
            ) : meta.beta ? (
              <span
                className="absolute top-1 right-1 text-[8px] px-1 rounded uppercase tracking-wider"
                style={{
                  background: 'rgb(var(--accent) / 0.18)',
                  color: 'rgb(var(--accent))',
                }}
              >
                Beta
              </span>
            ) : null}
          </button>
        );
      })}
    </div>
  );
}
