interface Props {
  score: number;
  benchmark?: number;
  height?: number;
}

type Segment = { from: number; to: number; label: string; color: string };
const SEGMENTS: Segment[] = [
  { from: 0, to: 25, label: 'Lacking', color: '#ff3860' },
  { from: 25, to: 50, label: 'Fair', color: '#fb7c1d' },
  { from: 50, to: 75, label: 'Good', color: '#f59e0b' },
  { from: 75, to: 100, label: 'Excellent', color: '#22c55e' },
];

function classify(score: number): { label: string; color: string } {
  for (const s of SEGMENTS) {
    if (score >= s.from && score <= s.to) return { label: s.label, color: s.color };
  }
  return { label: '—', color: '#6e7a96' };
}

export function ReadinessGauge({ score, benchmark = 60, height = 180 }: Props) {
  const cls = classify(score);
  const angle = -90 + (Math.min(100, Math.max(0, score)) / 100) * 180;
  const benchAngle = -90 + (Math.min(100, Math.max(0, benchmark)) / 100) * 180;

  const cx = 110;
  const cy = 110;
  const r = 90;
  const start = polar(cx, cy, r, -90);
  const end = polar(cx, cy, r, 90);

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="relative" style={{ height: height, width: 220 }}>
        <svg viewBox="0 0 220 130" className="h-full w-full">
          {/* segment arcs */}
          {SEGMENTS.map((s) => (
            <path
              key={s.label}
              d={arcPath(cx, cy, r, segAngle(s.from), segAngle(s.to))}
              stroke={s.color}
              strokeWidth={10}
              fill="none"
              opacity={0.3}
            />
          ))}
          {/* active arc up to score */}
          <path
            d={arcPath(cx, cy, r, -90, angle)}
            stroke={cls.color}
            strokeWidth={10}
            fill="none"
            strokeLinecap="round"
          />
          {/* tick marks */}
          {[0, 25, 50, 75, 100].map((p) => {
            const a = segAngle(p);
            const inner = polar(cx, cy, r - 8, a);
            const outer = polar(cx, cy, r + 8, a);
            return (
              <line
                key={p}
                x1={inner.x}
                y1={inner.y}
                x2={outer.x}
                y2={outer.y}
                stroke="#2c3a5c"
                strokeWidth={1}
              />
            );
          })}
          {/* benchmark needle */}
          <line
            x1={cx}
            y1={cy}
            x2={polar(cx, cy, r - 14, benchAngle).x}
            y2={polar(cx, cy, r - 14, benchAngle).y}
            stroke="#6e7a96"
            strokeWidth={1.5}
            strokeDasharray="2 2"
          />
          {/* main needle */}
          <line
            x1={cx}
            y1={cy}
            x2={polar(cx, cy, r - 4, angle).x}
            y2={polar(cx, cy, r - 4, angle).y}
            stroke={cls.color}
            strokeWidth={3}
            strokeLinecap="round"
          />
          <circle cx={cx} cy={cy} r={6} fill="#10172a" stroke={cls.color} strokeWidth={2} />
          {/* endpoints */}
          <circle cx={start.x} cy={start.y} r={2} fill="#6e7a96" />
          <circle cx={end.x} cy={end.y} r={2} fill="#6e7a96" />
        </svg>
        <div className="pointer-events-none absolute inset-0 grid place-items-center">
          <div className="mt-6 text-center">
            <div className="font-display text-3xl font-medium tabular-nums text-text-primary">
              {score}
              <span className="ml-0.5 text-base text-text-muted">%</span>
            </div>
            <div
              className="text-2xs font-mono uppercase tracking-wider"
              style={{ color: cls.color }}
            >
              {cls.label}
            </div>
          </div>
        </div>
      </div>
      <div className="grid w-full max-w-[260px] grid-cols-4 gap-1 text-center font-mono text-2xs">
        {SEGMENTS.map((s) => (
          <div key={s.label}>
            <div style={{ color: s.color }}>
              {s.from}-{s.to}
            </div>
            <div className="text-text-muted">{s.label}</div>
          </div>
        ))}
      </div>
      <div className="text-2xs font-mono text-text-muted">
        benchmark <span className="text-text-secondary">{benchmark}</span>
      </div>
    </div>
  );
}

function segAngle(pct: number): number {
  return -90 + (pct / 100) * 180;
}
function polar(cx: number, cy: number, r: number, deg: number) {
  const a = (deg * Math.PI) / 180;
  return { x: cx + r * Math.cos(a), y: cy + r * Math.sin(a) };
}
function arcPath(cx: number, cy: number, r: number, a1: number, a2: number) {
  const p1 = polar(cx, cy, r, a1);
  const p2 = polar(cx, cy, r, a2);
  const large = a2 - a1 > 180 ? 1 : 0;
  return `M ${p1.x} ${p1.y} A ${r} ${r} 0 ${large} 1 ${p2.x} ${p2.y}`;
}
