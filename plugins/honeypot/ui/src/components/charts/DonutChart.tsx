import React from 'react';
import '../AnalyticsTab.css'; // Assuming CSS is shared or moved. Ideally should be modularized too.

interface DonutChartProps {
  data: Array<{ label: string; value: number; color: string }>;
  size?: number;
  strokeWidth?: number;
  title: string;
}

const DonutChart: React.FC<DonutChartProps> = ({ data, size = 180, strokeWidth = 24, title }) => {
  const total = data.reduce((sum, item) => sum + item.value, 0);
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  let accumulatedOffset = 0;

  const segments = data.map((item, index) => {
    const percentage = total > 0 ? item.value / total : 0;
    const dashArray = circumference * percentage;
    const dashOffset = -accumulatedOffset;
    accumulatedOffset += dashArray;

    return (
      <circle
        key={index}
        className="analytics-donut-segment"
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke={item.color}
        strokeWidth={strokeWidth}
        strokeDasharray={`${dashArray} ${circumference - dashArray}`}
        strokeDashoffset={dashOffset}
        style={{ animationDelay: `${index * 0.1}s` }}
      />
    );
  });

  return (
    <div className="analytics-donut-container">
      <h4 className="analytics-donut-title">{title}</h4>
      <div className="analytics-donut-wrapper">
        <svg width={size} height={size} className="analytics-donut-svg">
          {/* Background circle */}
          <circle
            cx={size / 2}
            cy={size / 2}
            r={radius}
            fill="none"
            stroke="rgba(255,255,255,0.05)"
            strokeWidth={strokeWidth}
          />
          {/* Data segments */}
          {segments}
        </svg>
        <div className="analytics-donut-center">
          <span className="analytics-donut-total">{total}</span>
          <span className="analytics-donut-label">Total</span>
        </div>
      </div>
      {/* Legend */}
      <div className="analytics-donut-legend">
        {data
          .filter((d) => d.value > 0)
          .map((item, idx) => (
            <div key={idx} className="analytics-legend-item">
              <span className="analytics-legend-dot" style={{ background: item.color }} />
              <span className="analytics-legend-label">{item.label}</span>
              <span className="analytics-legend-value">{item.value}</span>
            </div>
          ))}
      </div>
    </div>
  );
};

export default DonutChart;
