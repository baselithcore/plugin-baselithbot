import { type LucideIcon } from "lucide-react";
import { cn } from "@/lib/cn";

interface Props {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  action,
  className,
}: Props) {
  return (
    <div
      className={cn(
        "flex h-full w-full flex-col items-center justify-center rounded-lg border border-dashed border-border bg-bg-panel-soft px-6 py-12 text-center animate-fade-in",
        className,
      )}
    >
      {Icon && (
        <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-md border border-border bg-bg-panel-elev">
          <Icon size={20} className="text-text-secondary" />
        </div>
      )}
      <p className="text-sm font-semibold text-text-primary">{title}</p>
      {description && (
        <p className="mt-1.5 max-w-sm text-xs leading-5 text-text-muted">
          {description}
        </p>
      )}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
