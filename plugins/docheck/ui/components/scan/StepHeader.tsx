import type { LucideIcon } from 'lucide-react';
import { cn } from '@/lib/cn';

export function StepHeader({
  idx,
  icon: Icon,
  title,
  hint,
}: {
  idx: number;
  icon: LucideIcon;
  title: string;
  hint?: string;
}) {
  return (
    <div className="flex items-start gap-3 mb-4">
      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md border border-border bg-bg-panel-elev font-mono text-[11px] text-text-muted">
        {String(idx).padStart(2, '0')}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 text-sm font-semibold text-text-primary">
          <Icon size={14} className="text-status-info" />
          {title}
        </div>
        {hint && <div className="text-[11px] text-text-muted mt-0.5">{hint}</div>}
      </div>
    </div>
  );
}

export function TabBtn({
  active,
  onClick,
  icon: Icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: LucideIcon;
  label: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'flex-1 flex items-center justify-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-colors',
        active
          ? 'bg-bg-panel-elev text-text-primary shadow-sm'
          : 'text-text-muted hover:text-text-primary'
      )}
    >
      <Icon size={12} />
      {label}
    </button>
  );
}
