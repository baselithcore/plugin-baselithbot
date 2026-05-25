/**
 * IOCCard - Display IOC count with icon
 */

interface IOCCardProps {
  icon: React.ReactNode;
  value: number;
  label: string;
  variant: 'ips' | 'domains' | 'hashes' | 'yara';
  onClick: () => void;
  disabled?: boolean;
}

export function IOCCard({ icon, value, label, variant, onClick, disabled }: IOCCardProps) {
  return (
    <div
      className={`ioc-card ${disabled ? 'disabled' : ''}`}
      onClick={disabled ? undefined : onClick}
    >
      <div className={`ioc-icon ${variant}`}>{icon}</div>
      <div className="ioc-info">
        <span className="ioc-value">{value}</span>
        <span className="ioc-label">{label}</span>
      </div>
    </div>
  );
}
