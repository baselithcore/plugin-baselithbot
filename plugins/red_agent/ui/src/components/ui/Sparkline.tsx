import ReactECharts from 'echarts-for-react';

interface SparklineProps {
  data: number[];
  color?: string;
  height?: number;
  area?: boolean;
}

export function Sparkline({ data, color = '#00e5ff', height = 40, area = true }: SparklineProps) {
  const option = {
    grid: { left: 0, right: 0, top: 2, bottom: 2 },
    xAxis: { type: 'category', show: false, boundaryGap: false, data: data.map((_, i) => i) },
    yAxis: { show: false, scale: true },
    tooltip: { show: false },
    animation: false,
    series: [
      {
        type: 'line',
        data,
        smooth: true,
        symbol: 'none',
        lineStyle: { color, width: 1.6 },
        areaStyle: area
          ? {
              color: {
                type: 'linear',
                x: 0,
                y: 0,
                x2: 0,
                y2: 1,
                colorStops: [
                  { offset: 0, color: `${color}40` },
                  { offset: 1, color: `${color}00` },
                ],
              },
            }
          : undefined,
      },
    ],
  };
  return (
    <ReactECharts option={option} style={{ height, width: '100%' }} opts={{ renderer: 'svg' }} />
  );
}
