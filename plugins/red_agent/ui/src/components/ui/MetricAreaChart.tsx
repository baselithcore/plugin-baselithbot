import ReactECharts from 'echarts-for-react';

interface Series {
  name: string;
  data: number[];
  color: string;
}

interface Props {
  xLabels: string[];
  series: Series[];
  height?: number;
  smooth?: boolean;
  showLegend?: boolean;
  yMin?: number;
}

export function MetricAreaChart({
  xLabels,
  series,
  height = 200,
  smooth = true,
  showLegend = false,
  yMin,
}: Props) {
  return (
    <ReactECharts
      opts={{ renderer: 'svg' }}
      style={{ height, width: '100%' }}
      option={{
        grid: { left: 32, right: 12, top: showLegend ? 28 : 14, bottom: 24 },
        legend: showLegend
          ? {
              top: 0,
              left: 0,
              icon: 'roundRect',
              itemWidth: 8,
              itemHeight: 8,
              textStyle: { color: '#a8b2cc', fontSize: 11, fontFamily: 'monospace' },
            }
          : undefined,
        tooltip: {
          trigger: 'axis',
          backgroundColor: '#10172a',
          borderColor: '#2c3a5c',
          textStyle: {
            color: '#e7ecf7',
            fontFamily: 'JetBrains Mono Variable, monospace',
            fontSize: 11,
          },
        },
        xAxis: {
          type: 'category',
          data: xLabels,
          axisLine: { lineStyle: { color: '#1f2942' } },
          axisLabel: { color: '#6e7a96', fontSize: 10, fontFamily: 'monospace' },
          axisTick: { show: false },
        },
        yAxis: {
          type: 'value',
          min: yMin,
          splitLine: { lineStyle: { color: '#1f2942', type: 'dashed' } },
          axisLine: { show: false },
          axisLabel: { color: '#6e7a96', fontSize: 10, fontFamily: 'monospace' },
        },
        series: series.map((s) => ({
          name: s.name,
          type: 'line',
          smooth,
          showSymbol: false,
          lineStyle: { width: 1.6, color: s.color },
          itemStyle: { color: s.color },
          areaStyle: {
            color: {
              type: 'linear',
              x: 0,
              y: 0,
              x2: 0,
              y2: 1,
              colorStops: [
                { offset: 0, color: `${s.color}50` },
                { offset: 1, color: `${s.color}05` },
              ],
            },
          },
          data: s.data,
        })),
      }}
    />
  );
}
