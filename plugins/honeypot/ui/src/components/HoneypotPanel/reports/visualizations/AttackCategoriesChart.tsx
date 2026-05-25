/**
 * Attack Categories Chart - Pie/Donut chart for attack distribution
 * Shows breakdown of attack types with percentages
 */

import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from 'recharts';

interface AttackCategoriesChartProps {
  categories: Record<string, number>;
  height?: number;
}

const COLORS = [
  '#ff4757', // Red
  '#ff6348', // Orange
  '#ffa502', // Yellow
  '#26de81', // Green
  '#00f5ff', // Cyan
  '#9d4edd', // Purple
  '#3742fa', // Blue
  '#f368e0', // Pink
  '#a4b0be', // Gray
];

export function AttackCategoriesChart({ categories, height = 300 }: AttackCategoriesChartProps) {
  if (!categories || Object.keys(categories).length === 0) {
    return (
      <div className="hp-chart-empty">
        <p>No category data available</p>
      </div>
    );
  }

  // Convert to array and sort by count
  const data = Object.entries(categories)
    .map(([name, value]) => ({ name, value }))
    .sort((a, b) => b.value - a.value)
    .slice(0, 9); // Top 9

  const total = data.reduce((sum, item) => sum + item.value, 0);

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0];
      const percentage = ((data.value / total) * 100).toFixed(1);
      return (
        <div
          style={{
            backgroundColor: 'rgba(0, 0, 0, 0.95)',
            border: '1px solid rgba(255, 255, 255, 0.2)',
            borderRadius: '8px',
            padding: '12px',
            minWidth: '160px',
          }}
        >
          <p style={{ color: '#fff', fontWeight: 'bold', marginBottom: '8px' }}>{data.name}</p>
          <p style={{ color: data.payload.fill, marginBottom: '4px' }}>
            Count: {data.value.toLocaleString()}
          </p>
          <p style={{ color: '#00f5ff' }}>{percentage}% of total</p>
        </div>
      );
    }
    return null;
  };

  const renderCustomLabel = (entry: any) => {
    const percentage = ((entry.value / total) * 100).toFixed(0);
    return `${percentage}%`;
  };

  return (
    <div className="hp-chart-container">
      <ResponsiveContainer width="100%" height={height} minWidth={100}>
        <PieChart>
          <Pie
            data={data}
            cx="50%"
            cy="50%"
            labelLine={false}
            label={renderCustomLabel}
            outerRadius={100}
            innerRadius={60}
            fill="#8884d8"
            dataKey="value"
            animationDuration={800}
            animationBegin={0}
          >
            {data.map((_, index) => (
              <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip content={<CustomTooltip />} />
          <Legend
            verticalAlign="bottom"
            height={36}
            wrapperStyle={{ paddingTop: '20px', fontSize: '12px' }}
            formatter={(value, entry: any) => {
              const percentage = ((entry.payload.value / total) * 100).toFixed(1);
              return `${value} (${percentage}%)`;
            }}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
