import ReactECharts from 'echarts-for-react';
import type { Severity } from '../../lib/api';

const COLORS: Record<Severity, string> = {
  info: '#4cc9f0',
  low: '#2dd4bf',
  medium: '#f59e0b',
  high: '#fb7c1d',
  critical: '#ff3860',
};

interface DonutProps {
  data: Record<Severity, number>;
  height?: number;
  centerLabel?: string;
  centerValue?: string;
}

export function SeverityDonut({
  data,
  height = 220,
  centerLabel = 'Total',
  centerValue,
}: DonutProps) {
  const total = Object.values(data).reduce((a, b) => a + b, 0);
  const series = (Object.keys(data) as Severity[])
    .filter((k) => data[k] > 0)
    .map((k) => ({ name: k, value: data[k], itemStyle: { color: COLORS[k] } }));

  const option = {
    tooltip: {
      trigger: 'item',
      backgroundColor: '#10172a',
      borderColor: '#2c3a5c',
      textStyle: {
        color: '#e7ecf7',
        fontFamily: 'JetBrains Mono Variable, monospace',
        fontSize: 11,
      },
    },
    series: [
      {
        type: 'pie',
        radius: ['62%', '88%'],
        avoidLabelOverlap: false,
        label: { show: false },
        labelLine: { show: false },
        emphasis: {
          scale: false,
          itemStyle: { shadowBlur: 8, shadowColor: 'rgba(0,229,255,0.3)' },
        },
        data:
          series.length > 0
            ? series
            : [{ name: 'empty', value: 1, itemStyle: { color: '#1f2942' } }],
      },
    ],
  };

  return (
    <div className="relative">
      <ReactECharts option={option} style={{ height, width: '100%' }} opts={{ renderer: 'svg' }} />
      <div className="pointer-events-none absolute inset-0 grid place-items-center">
        <div className="text-center">
          <div className="font-display text-3xl font-medium tabular-nums text-text-primary">
            {centerValue ?? total}
          </div>
          <div className="mt-0.5 text-2xs uppercase tracking-wider text-text-muted">
            {centerLabel}
          </div>
        </div>
      </div>
    </div>
  );
}
