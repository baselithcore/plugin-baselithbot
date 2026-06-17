// Reusable area+line sparkline over a numeric series. Returns null below two
// points (a single sample can't draw a trend). Stroke uses the accent token;
// non-scaling so it stays crisp under preserveAspectRatio="none".
export function Sparkline({ data, height = 40 }: { data: number[]; height?: number }) {
  if (data.length < 2) return null;

  const width = 240;
  const padding = 4;
  const minVal = Math.min(...data) * 0.95;
  const maxVal = Math.max(...data) * 1.05 || 1;
  const range = Math.max(maxVal - minVal, 1);

  const points = data.map((val, idx) => {
    const x = (idx / (data.length - 1)) * (width - padding * 2) + padding;
    const y = height - ((val - minVal) / range) * (height - padding * 2) - padding;
    return `${x},${y}`;
  });

  const line = `M ${points.join(' L ')}`;
  const area = `${line} L ${width - padding},${height} L ${padding},${height} Z`;
  const gradId = `spark-${data.length}-${Math.round(data[data.length - 1])}`;

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="none"
      className="w-full overflow-visible"
      style={{ height }}
      aria-hidden
    >
      <defs>
        <linearGradient id={gradId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="var(--accent)" stopOpacity="0.16" />
          <stop offset="100%" stopColor="var(--accent)" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill={`url(#${gradId})`} />
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
