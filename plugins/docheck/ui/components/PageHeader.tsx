import { type LucideIcon } from "lucide-react";
import { cn } from "@/lib/cn";

interface Props {
  eyebrow?: string;
  eyebrowIcon?: LucideIcon;
  title: string;
  description?: string;
  actions?: React.ReactNode;
  className?: string;
}

export function PageHeader({
  eyebrow,
  eyebrowIcon: Icon,
  title,
  description,
  actions,
  className,
}: Props) {
  return (
    <div
      className={cn(
        "mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between",
        className,
      )}
    >
      <div className="min-w-0">
        {eyebrow && (
          <div className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-text-muted">
            {Icon && <Icon size={13} />}
            {eyebrow}
          </div>
        )}
        <h1 className="mt-2 text-[24px] leading-tight font-semibold tracking-tight text-text-primary">
          {title}
        </h1>
        {description && (
          <p className="mt-2 max-w-2xl text-sm text-text-muted leading-6">
            {description}
          </p>
        )}
      </div>
      {actions && (
        <div className="flex items-center gap-2 shrink-0">{actions}</div>
      )}
    </div>
  );
}
