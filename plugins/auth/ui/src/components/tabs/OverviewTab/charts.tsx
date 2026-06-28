/**
 * Minimal, dependency-free SVG/CSS chart primitives for the Overview console.
 * Restrained on purpose — an operations dashboard reads better with hairlines,
 * tabular figures and thin meters than with gradient candy. Colors come from the
 * `--admin-*` tokens so everything themes light/dark.
 */

interface AreaChartProps {
  values: number[];
  height?: number;
}

/** Activity trend: hairline baseline, faint fill, 1px line. */
export const AreaChart = ({ values, height = 84 }: AreaChartProps) => {
  const w = 100;
  const h = height;
  const max = Math.max(1, ...values);
  const n = values.length;
  const x = (i: number) => (n <= 1 ? 0 : (i / (n - 1)) * w);
  const y = (v: number) => h - (v / max) * (h - 10) - 5;
  const line = values
    .map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(2)},${y(v).toFixed(2)}`)
    .join(' ');
  const area = `${line} L${w},${h} L0,${h} Z`;
  return (
    <svg
      className="ov-area"
      viewBox={`0 0 ${w} ${h}`}
      preserveAspectRatio="none"
      width="100%"
      height={h}
      role="img"
      aria-hidden="true"
    >
      <defs>
        <linearGradient id="ov-area-grad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="var(--admin-accent)" stopOpacity="0.14" />
          <stop offset="1" stopColor="var(--admin-accent)" stopOpacity="0" />
        </linearGradient>
      </defs>
      <line
        x1="0"
        y1={h - 0.5}
        x2={w}
        y2={h - 0.5}
        stroke="var(--admin-table-border)"
        strokeWidth="1"
        vectorEffect="non-scaling-stroke"
      />
      <path d={area} fill="url(#ov-area-grad)" />
      <path
        d={line}
        fill="none"
        stroke="var(--admin-accent)"
        strokeWidth="1.5"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
};

interface MeterProps {
  pct: number;
  tone?: 'accent' | 'success' | 'warning' | 'danger';
}

/** Thin horizontal progress meter — solid, not gradient. */
export const Meter = ({ pct, tone = 'accent' }: MeterProps) => (
  <span className="ov-meter">
    <span
      className={`ov-meter-fill tone-${tone}`}
      style={{ width: `${Math.max(0, Math.min(100, pct))}%` }}
    />
  </span>
);
