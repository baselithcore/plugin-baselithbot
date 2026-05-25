/**
 * EmptyState - Display empty state with icon and message
 */

interface EmptyStateProps {
  icon: React.ReactNode;
  message: string;
}

export function EmptyState({ icon, message }: EmptyStateProps) {
  return (
    <div className="sinkhole-empty">
      {icon}
      <span>{message}</span>
    </div>
  );
}
