/**
 * Geographic Distribution Chart - Top attacking countries
 * Bar chart with country flags and attack counts
 */

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { GeoDistribution } from '../../../types';

interface GeoDistributionChartProps {
  data: GeoDistribution[];
  height?: number;
  topN?: number;
}

// Color palette for countries
const COLORS = [
  '#9d4edd', // Cyber purple
  '#00f5ff', // Cyber cyan
  '#ff4757', // Red
  '#ff6348', // Orange
  '#ffa502', // Yellow
  '#26de81', // Green
  '#3742fa', // Blue
  '#f368e0', // Pink
];

export function GeoDistributionChart({ data, height = 350, topN = 10 }: GeoDistributionChartProps) {
  if (!data?.length) {
    return (
      <div className="hp-chart-empty">
        <p>No geographic data available</p>
      </div>
    );
  }

  // Take top N countries by attack count
  const topCountries = data.slice(0, topN).map((geo, idx) => ({
    name: geo.country_name,
    code: geo.country_code,
    attacks: geo.attack_count,
    ips: geo.unique_ips,
    color: COLORS[idx % COLORS.length],
  }));

  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div
          style={{
            backgroundColor: 'rgba(0, 0, 0, 0.95)',
            border: '1px solid rgba(255, 255, 255, 0.2)',
            borderRadius: '8px',
            padding: '12px',
            minWidth: '180px',
          }}
        >
          <p style={{ color: '#fff', fontWeight: 'bold', marginBottom: '8px' }}>
            {data.name} ({data.code})
          </p>
          <p style={{ color: '#ff4757', marginBottom: '4px' }}>
            🎯 Attacks: {data.attacks.toLocaleString()}
          </p>
          <p style={{ color: '#00f5ff' }}>📍 Unique IPs: {data.ips.toLocaleString()}</p>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="hp-chart-container">
      <ResponsiveContainer width="100%" height={height} minWidth={100}>
        <BarChart data={topCountries} margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
          <XAxis
            dataKey="name"
            stroke="rgba(255,255,255,0.5)"
            angle={-45}
            textAnchor="end"
            height={80}
            tick={{ fontSize: 11 }}
          />
          <YAxis
            stroke="rgba(255,255,255,0.5)"
            tick={{ fontSize: 11 }}
            label={{
              value: 'Attack Count',
              angle: -90,
              position: 'insideLeft',
              style: { fill: 'rgba(255,255,255,0.7)' },
            }}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255, 255, 255, 0.05)' }} />
          <Bar dataKey="attacks" radius={[8, 8, 0, 0]} animationDuration={800}>
            {topCountries.map((entry, index) => (
              <Cell key={`cell-${index}`} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
