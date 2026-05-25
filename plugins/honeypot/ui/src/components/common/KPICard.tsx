import React from 'react';
import '../AnalyticsTab.css';

interface KPICardProps {
  icon: React.ReactNode;
  label: string;
  value: number | string;
  subValue?: string;
  trend?: 'up' | 'down' | 'neutral';
  accentColor?: string;
}

const KPICard: React.FC<KPICardProps> = ({
  icon,
  label,
  value,
  subValue,
  trend,
  accentColor = '#ff4757',
}) => (
  <div className="analytics-kpi-card" style={{ '--accent': accentColor } as React.CSSProperties}>
    <div className="analytics-kpi-icon">{icon}</div>
    <div className="analytics-kpi-content">
      <span className="analytics-kpi-label">{label}</span>
      <div className="analytics-kpi-value-row">
        <span className="analytics-kpi-value">{value}</span>
        {trend && (
          <span className={`analytics-kpi-trend ${trend}`}>
            {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '→'}
          </span>
        )}
      </div>
      {subValue && <span className="analytics-kpi-sub">{subValue}</span>}
    </div>
  </div>
);

export default KPICard;
