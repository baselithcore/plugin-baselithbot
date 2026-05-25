/**
 * Animated Metric Card - Counter with trend indicator
 * Animated number counting effect for KPIs
 */

import { useEffect, useState } from 'react';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface AnimatedMetricProps {
  value: number;
  label: string;
  icon?: React.ReactNode;
  color?: string;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: number;
  suffix?: string;
  prefix?: string;
  decimals?: number;
}

export function AnimatedMetric({
  value,
  label,
  icon,
  color = 'var(--hp-primary)',
  trend,
  trendValue,
  suffix = '',
  prefix = '',
  decimals = 0,
}: AnimatedMetricProps) {
  const [displayValue, setDisplayValue] = useState(0);

  useEffect(() => {
    const duration = 1000; // 1 second animation
    const steps = 60;
    const increment = value / steps;
    let current = 0;
    let step = 0;

    const timer = setInterval(() => {
      step++;
      current = Math.min(current + increment, value);
      setDisplayValue(current);

      if (step >= steps) {
        setDisplayValue(value);
        clearInterval(timer);
      }
    }, duration / steps);

    return () => clearInterval(timer);
  }, [value]);

  const formatValue = (v: number) => {
    if (decimals > 0) {
      return v.toFixed(decimals);
    }
    return Math.round(v).toLocaleString();
  };

  const getTrendIcon = () => {
    if (!trend) return null;
    if (trend === 'up') return <TrendingUp size={14} />;
    if (trend === 'down') return <TrendingDown size={14} />;
    return <Minus size={14} />;
  };

  const getTrendColor = () => {
    if (!trend) return 'transparent';
    if (trend === 'up') return '#26de81';
    if (trend === 'down') return '#ff4757';
    return '#a4b0be';
  };

  return (
    <div className="hp-animated-metric" style={{ '--metric-color': color } as React.CSSProperties}>
      {icon && <div className="hp-metric-icon">{icon}</div>}
      <div className="hp-metric-content">
        <div className="hp-metric-value">
          {prefix}
          {formatValue(displayValue)}
          {suffix}
        </div>
        <div className="hp-metric-label">{label}</div>
        {trend && trendValue !== undefined && (
          <div className="hp-metric-trend" style={{ color: getTrendColor() }}>
            {getTrendIcon()}
            <span>{Math.abs(trendValue).toFixed(1)}%</span>
          </div>
        )}
      </div>
    </div>
  );
}
