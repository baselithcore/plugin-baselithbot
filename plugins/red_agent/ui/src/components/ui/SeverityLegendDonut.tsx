import ReactECharts from 'echarts-for-react';
import type { Severity } from '../../lib/api';
import { Icon } from './Icon';

const COLOR: Record<Severity, string> = {
  info: '#4cc9f0',
  low: '#2dd4bf',
  medium: '#f59e0b',
  high: '#fb7c1d',
  critical: '#ff3860',
};

const LABEL: Record<Severity, string> = {
  info: 'Info',
  low: 'Low',
  medium: 'Medium',
  high: 'High',
  critical: 'Critical',
};

const ABBR: Record<Severity, string> = {
  info: 'I',
  low: 'L',
  medium: 'M',
  high: 'H',
  critical: 'C',
};

const ORDER: Severity[] = ['critical', 'high', 'medium', 'low', 'info'];

interface Props {
  data: Record<Severity, number>;
  deltas?: Partial<Record<Severity, { value: string; direction: 'up' | 'down' }>>;
  height?: number;
}

export function SeverityLegendDonut({ data, deltas, height = 200 }: Props) {
  const total = ORDER.reduce((a, k) => a + data[k], 0);
  const series = ORDER.filter((k) => data[k] > 0).map((k) => ({
    name: LABEL[k],
    value: data[k],
    itemStyle: { color: COLOR[k] },
  }));

  return (
    <div className="grid items-center gap-5 md:grid-cols-[auto_1fr]">
      <div className="relative">
        <ReactECharts
          opts={{ renderer: 'svg' }}
          style={{ height, width: height }}
          option={{
            tooltip: {
              trigger: 'item',
              backgroundColor: '#10172a',
              borderColor: '#2c3a5c',
              textStyle: { color: '#e7ecf7', fontSize: 11, fontFamily: 'monospace' },
            },
            series: [
              {
                type: 'pie',
                radius: ['65%', '92%'],
                avoidLabelOverlap: false,
                label: { show: false },
                labelLine: { show: false },
                emphasis: { scale: false },
                data:
                  series.length > 0
                    ? series
                    : [{ name: 'empty', value: 1, itemStyle: { color: '#1f2942' } }],
              },
            ],
          }}
        />
        <div className="pointer-events-none absolute inset-0 grid place-items-center">
          <div className="text-center">
            <div className="font-display text-2xl font-medium tabular-nums text-text-primary">
              {total}
            </div>
            <div className="text-2xs uppercase tracking-wider text-text-muted">Total</div>
          </div>
        </div>
      </div>

      <ul className="space-y-2.5">
        {ORDER.map((k) => {
          const v = data[k];
          const pct = total > 0 ? Math.round((v / total) * 100) : 0;
          const d = deltas?.[k];
          return (
            <li
              key={k}
              className="flex items-center justify-between gap-3 rounded-md px-2 py-1.5 transition-colors hover:bg-bg-hover/40"
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <span
                  aria-hidden
                  className="grid h-5 w-5 shrink-0 place-items-center rounded font-mono text-[10px] font-bold"
                  style={{
                    background: `${COLOR[k]}1f`,
                    color: COLOR[k],
                    boxShadow: `inset 0 0 0 1px ${COLOR[k]}55`,
                  }}
                >
                  {ABBR[k]}
                </span>
                <div className="min-w-0">
                  <div className="font-display text-base font-medium tabular-nums text-text-primary">
                    {v}
                  </div>
                  <div className="text-2xs text-text-muted">{LABEL[k]} Issues</div>
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                {d && (
                  <span
                    className={`inline-flex items-center gap-0.5 text-2xs font-mono ${
                      d.direction === 'down' ? 'text-status-success' : 'text-sev-critical'
                    }`}
                  >
                    {d.direction === 'up' ? (
                      <Icon.ArrowUp size={10} />
                    ) : (
                      <Icon.ArrowDown size={10} />
                    )}
                    {d.value}
                  </span>
                )}
                <span className="font-mono text-2xs text-text-muted">{pct}%</span>
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
