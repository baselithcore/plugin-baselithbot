import { ReactNode } from 'react';

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: ReactNode;
  action?: ReactNode;
  compact?: boolean;
}

export function EmptyState({ icon, title, description, action, compact }: EmptyStateProps) {
  return (
    <div className={`grid place-items-center text-center ${compact ? 'py-10' : 'py-16'}`}>
      <div className="max-w-md">
        {icon && (
          <div className="mb-3 inline-flex h-8 w-8 items-center justify-center text-text-subtle">
            {icon}
          </div>
        )}
        <h3 className="font-display text-lg text-text-primary">{title}</h3>
        {description && <p className="mt-1.5 text-sm text-text-muted">{description}</p>}
        {action && <div className="mt-5 flex justify-center gap-2">{action}</div>}
      </div>
    </div>
  );
}
