/**
 * Tiny dependency-free SVG chart primitives for the Overview dashboard.
 * They read theme colors from the `--admin-*` tokens so they re-skin light/dark
 * for free. Deliberately minimal — an overview needs glanceable shapes, not a
 * charting library and its bundle cost.
 */

interface AreaChartProps {
  values: number[];
  height?: number;
}

/** Smooth-ish area + line spark for a time series. */
export const AreaChart = ({ values, height = 72 }: AreaChartProps) => {
  const w = 100;
  const h = height;
  const max = Math.max(1, ...values);
  const n = values.length;
  const pts = values.map((v, i): [number, number] => [
    n <= 1 ? 0 : (i / (n - 1)) * w,
    h - (v / max) * (h - 8) - 4,
  ]);
  const line = pts.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(2)},${p[1].toFixed(2)}`).join(' ');
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
          <stop offset="0" stopColor="var(--admin-accent)" stopOpacity="0.26" />
          <stop offset="1" stopColor="var(--admin-accent)" stopOpacity="0" />
        </linearGradient>
      </defs>
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

export interface BarItem {
  label: string;
  value: number;
}

interface BarListProps {
  items: BarItem[];
  format?: (v: number) => string;
}

/** Horizontal labelled bars, normalized to the largest value. */
export const BarList = ({ items, format }: BarListProps) => {
  const max = Math.max(1, ...items.map((i) => i.value));
  return (
    <div className="ov-bars">
      {items.map((it) => (
        <div className="ov-bar-row" key={it.label}>
          <span className="ov-bar-label" title={it.label}>
            {it.label}
          </span>
          <span className="ov-bar-track">
            <span className="ov-bar-fill" style={{ width: `${(it.value / max) * 100}%` }} />
          </span>
          <span className="ov-bar-val">{format ? format(it.value) : it.value}</span>
        </div>
      ))}
    </div>
  );
};

interface DonutProps {
  pct: number;
  center: string;
  caption: string;
}

/** Single-value progress ring with a centered figure. */
export const Donut = ({ pct, center, caption }: DonutProps) => {
  const r = 34;
  const c = 2 * Math.PI * r;
  const dash = (Math.max(0, Math.min(100, pct)) / 100) * c;
  return (
    <div className="ov-donut">
      <svg viewBox="0 0 80 80" width="96" height="96" role="img" aria-label={caption}>
        <circle cx="40" cy="40" r={r} fill="none" stroke="var(--admin-surface-2)" strokeWidth="9" />
        <circle
          cx="40"
          cy="40"
          r={r}
          fill="none"
          stroke="var(--admin-accent)"
          strokeWidth="9"
          strokeLinecap="round"
          strokeDasharray={`${dash} ${c}`}
          transform="rotate(-90 40 40)"
        />
      </svg>
      <div className="ov-donut-center">
        <strong>{center}</strong>
        <span>{caption}</span>
      </div>
    </div>
  );
};
