/**
 * Severity Distribution Chart - Radial bar chart for severity levels
 * Shows distribution of Critical/High/Medium/Low events
 */

import {
  RadialBarChart,
  RadialBar,
  Legend,
  ResponsiveContainer,
  PolarAngleAxis,
  Tooltip,
} from 'recharts';
import { ThreatSummary } from '../../../types';

interface SeverityDistributionChartProps {
  summary: ThreatSummary;
  height?: number;
}

export function SeverityDistributionChart({
  summary,
  height = 300,
}: SeverityDistributionChartProps) {
  const data = [
    {
      name: 'Critical',
      value: summary.critical_events,
      fill: '#ff4757',
    },
    {
      name: 'High',
      value: summary.high_events,
      fill: '#ff6348',
    },
    {
      name: 'Medium',
      value: summary.medium_events,
      fill: '#ffa502',
    },
    {
      name: 'Low',
      value: summary.low_events,
      fill: '#26de81',
    },
  ].filter((item) => item.value > 0); // Only show non-zero

  const total = data.reduce((sum, item) => sum + item.value, 0);

  if (total === 0) {
    return (
      <div className="hp-chart-empty">
        <p>No severity data available</p>
      </div>
    );
  }

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      const percentage = ((data.value / total) * 100).toFixed(1);
      return (
        <div
          style={{
            backgroundColor: 'rgba(0, 0, 0, 0.95)',
            border: '1px solid rgba(255, 255, 255, 0.2)',
            borderRadius: '8px',
            padding: '12px',
          }}
        >
          <p style={{ color: '#fff', fontWeight: 'bold', marginBottom: '8px' }}>
            {data.name} Severity
          </p>
          <p style={{ color: data.fill, marginBottom: '4px' }}>
            Count: {data.value.toLocaleString()}
          </p>
          <p style={{ color: '#00f5ff' }}>{percentage}% of total events</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="hp-chart-container">
      <ResponsiveContainer width="100%" height={height} minWidth={100}>
        <RadialBarChart
          cx="50%"
          cy="50%"
          innerRadius="20%"
          outerRadius="90%"
          barSize={20}
          data={data}
        >
          <PolarAngleAxis
            type="number"
            domain={[0, Math.max(...data.map((d) => d.value))]}
            angleAxisId={0}
            tick={false}
          />
          <RadialBar
            label={{ position: 'insideStart', fill: '#fff', fontSize: 12 }}
            background
            dataKey="value"
            animationDuration={800}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            iconSize={10}
            layout="vertical"
            verticalAlign="middle"
            align="right"
            wrapperStyle={{ paddingLeft: '20px', fontSize: '12px' }}
            formatter={(value, entry: any) => {
              const percentage = ((entry.payload.value / total) * 100).toFixed(1);
              return `${value}: ${entry.payload.value} (${percentage}%)`;
            }}
          />
        </RadialBarChart>
      </ResponsiveContainer>
    </div>
  );
}
