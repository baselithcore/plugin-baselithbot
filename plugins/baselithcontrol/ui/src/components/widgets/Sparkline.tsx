interface Props {
  data: number[];
  width?: number;
  height?: number;
  id: string; // unique gradient id (multiple sparklines share one SVG namespace)
}

// Minimal area+line sparkline over a numeric series. Self-scaling; renders a
// flat baseline until at least two points exist.
export function Sparkline({ data, width = 120, height = 36, id }: Props) {
  const pad = 3;
  if (data.length < 2) {
    return (
      <svg
        viewBox={`0 0 ${width} ${height}`}
        preserveAspectRatio="none"
        className="h-9 w-full"
        aria-hidden
      >
        <line
          x1={pad}
          y1={height - pad}
          x2={width - pad}
          y2={height - pad}
          stroke="var(--border-strong)"
          strokeWidth="1.5"
          strokeLinecap="round"
          vectorEffect="non-scaling-stroke"
        />
      </svg>
    );
  }

  const min = Math.min(...data) * 0.95;
  const max = Math.max(...data) * 1.05 || 1;
  const range = Math.max(max - min, 1e-6);

  const pts = data.map((v, i) => {
    const x = (i / (data.length - 1)) * (width - pad * 2) + pad;
    const y = height - ((v - min) / range) * (height - pad * 2) - pad;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const line = `M ${pts.join(' L ')}`;
  const area = `${line} L ${width - pad},${height} L ${pad},${height} Z`;

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      className="h-9 w-full overflow-visible"
      aria-hidden
    >
      <defs>
        <linearGradient id={`spark-${id}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.22" />
          <stop offset="100%" stopColor="var(--accent)" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#spark-${id})`} />
      <path
        d={line}
        fill="none"
        stroke="var(--accent)"
        strokeWidth="1.75"
        strokeLinecap="round"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      />
    </svg>
  );
}
