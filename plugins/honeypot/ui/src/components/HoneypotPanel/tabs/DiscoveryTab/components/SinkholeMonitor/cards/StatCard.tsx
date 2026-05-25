/**
 * StatCard - Display a statistic with icon and label
 */

interface StatCardProps {
  icon: React.ReactNode;
  value: number;
  label: string;
  variant?: 'default' | 'danger' | 'warning' | 'success' | 'purple';
}

export function StatCard({ icon, value, label, variant = 'default' }: StatCardProps) {
  return (
    <div className="sinkhole-stat-card">
      <div className="sinkhole-stat-header">
        <div className={`sinkhole-stat-icon ${variant}`}>{icon}</div>
      </div>
      <div className="sinkhole-stat-value">{value}</div>
      <div className="sinkhole-stat-label">{label}</div>
    </div>
  );
}
