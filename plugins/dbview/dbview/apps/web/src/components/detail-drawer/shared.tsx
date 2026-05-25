import { Search, X } from 'lucide-react';
import { toast } from 'sonner';

export function copyToClipboard(text: string, msg: string) {
  navigator.clipboard.writeText(text);
  toast.success(msg);
}

export function FilterBar({
  value,
  onChange,
  placeholder,
  count,
  total,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder: string;
  count: number;
  total: number;
}) {
  return (
    <div
      className="flex items-center gap-2 px-3 h-8 mb-2 rounded-md border"
      style={{
        background: 'rgb(var(--surface-2) / 0.4)',
        borderColor: 'rgb(var(--border-subtle))',
      }}
    >
      <Search className="w-3.5 h-3.5 text-text-dim shrink-0" />
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Escape' && value) {
            e.stopPropagation();
            onChange('');
          }
        }}
        placeholder={placeholder}
        aria-label={placeholder}
        className="bg-transparent flex-1 outline-none text-[12px] placeholder:text-text-dim"
      />
      <span className="text-[10px] font-mono text-text-dim shrink-0">
        {value ? `${count}/${total}` : `${total}`}
      </span>
      {value && (
        <button
          onClick={() => onChange('')}
          className="btn-icon w-5 h-5"
          aria-label="Clear filter"
          title="Clear"
        >
          <X className="w-3 h-3" />
        </button>
      )}
    </div>
  );
}

export interface RelationEntry {
  from: string;
  to: string;
  constraint?: string;
  /** Entity ids (tables / labels) participating in this edge — used to highlight on hover. */
  entityIds?: string[];
}

export function RelationsBlock({
  title,
  icon,
  edges,
  onHover,
}: {
  title: string;
  icon: React.ReactNode;
  edges: RelationEntry[];
  onHover?: (ids: string[] | null) => void;
}) {
  return (
    <div className="mb-4">
      <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-text-dim mb-2">
        {icon}
        <span>
          {title} ({edges.length})
        </span>
      </div>
      {edges.length === 0 && <div className="text-[12px] text-text-dim italic">none</div>}
      <div className="flex flex-col gap-1">
        {edges.map((e, i) => (
          <div
            key={i}
            onMouseEnter={() => e.entityIds && onHover?.(e.entityIds)}
            onMouseLeave={() => e.entityIds && onHover?.(null)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-md text-[11px] font-mono transition-colors hover:bg-accent/10 hover:ring-1 hover:ring-accent/40 cursor-default"
            style={{
              background: 'rgb(var(--surface-2) / 0.44)',
              border: '1px solid rgb(var(--border-subtle) / 0.58)',
            }}
          >
            <span className="text-text-muted truncate">{e.from}</span>
            <span className="text-text-dim">→</span>
            <span className="text-text truncate">{e.to}</span>
            {e.constraint && (
              <span className="ml-auto text-[9px] text-text-dim font-mono shrink-0">
                {e.constraint}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
