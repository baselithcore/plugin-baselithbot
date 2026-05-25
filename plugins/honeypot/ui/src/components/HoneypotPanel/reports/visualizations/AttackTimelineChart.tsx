/**
 * Attack Timeline Chart - Interactive timeline visualization
 * Shows attack events over time with severity coloring
 */

import { useMemo } from 'react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Brush,
} from 'recharts';
import { AttackTimelineEntry } from '../../../types';

interface AttackTimelineChartProps {
  timeline: AttackTimelineEntry[];
  height?: number;
}

export function AttackTimelineChart({ timeline, height = 300 }: AttackTimelineChartProps) {
  // Aggregate events by hour and severity
  const chartData = useMemo(() => {
    if (!timeline?.length) return [];

    // Group by hour
    const hourMap = new Map<
      string,
      { hour: string; critical: number; high: number; medium: number; low: number; total: number }
    >();

    timeline.forEach((event) => {
      const date = new Date(event.timestamp);
      const hourKey = `${date.toLocaleDateString()} ${date.getHours()}:00`;

      if (!hourMap.has(hourKey)) {
        hourMap.set(hourKey, { hour: hourKey, critical: 0, high: 0, medium: 0, low: 0, total: 0 });
      }

      const entry = hourMap.get(hourKey)!;
      const severity = event.severity.toLowerCase();

      if (severity === 'critical') entry.critical++;
      else if (severity === 'high') entry.high++;
      else if (severity === 'medium') entry.medium++;
      else entry.low++;

      entry.total++;
    });

    return Array.from(hourMap.values()).sort((a, b) => a.hour.localeCompare(b.hour));
  }, [timeline]);

  if (!chartData.length) {
    return (
      <div className="hp-chart-empty">
        <p>No timeline data available</p>
      </div>
    );
  }

  return (
    <div className="hp-chart-container">
      <ResponsiveContainer width="100%" height={height} minWidth={100}>
        <AreaChart data={chartData} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="colorCritical" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ff4757" stopOpacity={0.8} />
              <stop offset="95%" stopColor="#ff4757" stopOpacity={0.1} />
            </linearGradient>
            <linearGradient id="colorHigh" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ff6348" stopOpacity={0.8} />
              <stop offset="95%" stopColor="#ff6348" stopOpacity={0.1} />
            </linearGradient>
            <linearGradient id="colorMedium" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ffa502" stopOpacity={0.8} />
              <stop offset="95%" stopColor="#ffa502" stopOpacity={0.1} />
            </linearGradient>
            <linearGradient id="colorLow" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#26de81" stopOpacity={0.8} />
              <stop offset="95%" stopColor="#26de81" stopOpacity={0.1} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.1)" />
          <XAxis
            dataKey="hour"
            stroke="rgba(255,255,255,0.5)"
            tick={{ fontSize: 11 }}
            tickFormatter={(value) => {
              const parts = value.split(' ');
              return parts[parts.length - 1]; // Just show time
            }}
          />
          <YAxis stroke="rgba(255,255,255,0.5)" tick={{ fontSize: 11 }} />
          <Tooltip
            contentStyle={{
              backgroundColor: 'rgba(0, 0, 0, 0.9)',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              borderRadius: '8px',
              padding: '12px',
            }}
            labelStyle={{ color: '#fff', marginBottom: '8px' }}
          />
          <Legend wrapperStyle={{ paddingTop: '20px' }} />
          <Area
            type="monotone"
            dataKey="critical"
            stackId="1"
            stroke="#ff4757"
            fill="url(#colorCritical)"
            name="Critical"
          />
          <Area
            type="monotone"
            dataKey="high"
            stackId="1"
            stroke="#ff6348"
            fill="url(#colorHigh)"
            name="High"
          />
          <Area
            type="monotone"
            dataKey="medium"
            stackId="1"
            stroke="#ffa502"
            fill="url(#colorMedium)"
            name="Medium"
          />
          <Area
            type="monotone"
            dataKey="low"
            stackId="1"
            stroke="#26de81"
            fill="url(#colorLow)"
            name="Low"
          />
          <Brush dataKey="hour" height={30} stroke="rgba(255,255,255,0.2)" fill="rgba(0,0,0,0.3)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}
