import { useState } from 'react';
import { Icon } from '../../components/ui';

export function FilterPill({
  label,
  value,
  onClear,
  renderInput,
}: {
  label: string;
  value: string;
  onClear: () => void;
  renderInput: () => React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((o) => !o)}
        className={`inline-flex h-7 items-center gap-1.5 rounded border px-2 text-xs transition-colors ${
          value
            ? 'border-brand/50 bg-brand/10 text-brand'
            : 'border-bg-line bg-bg-elevated text-text-secondary hover:border-bg-line-strong'
        }`}
      >
        <Icon.Filter2 size={11} />
        <span>
          {label}
          {value && <span className="ml-1 font-mono text-2xs">: {value}</span>}
        </span>
        {value ? (
          <span
            role="button"
            tabIndex={0}
            onClick={(e) => {
              e.stopPropagation();
              onClear();
            }}
            className="ml-0.5 grid h-3.5 w-3.5 place-items-center rounded-full hover:bg-brand/20"
          >
            <Icon.X size={9} />
          </span>
        ) : (
          <Icon.ChevronDown size={11} className="text-text-muted" />
        )}
      </button>
      {open && (
        <div className="absolute left-0 top-9 z-30 min-w-[200px] rounded-md border border-bg-line bg-bg-elevated p-2 shadow-elevated">
          {renderInput()}
          <button
            type="button"
            onClick={() => setOpen(false)}
            className="mt-2 w-full rounded bg-brand/10 py-1 text-xs font-medium text-brand hover:bg-brand/20"
          >
            Apply
          </button>
        </div>
      )}
    </div>
  );
}
