interface Props {
  score: number;
  size?: number;
  /** When true, render `—` instead of a numeric score (e.g. 0 evaluated rules). */
  indeterminate?: boolean;
}

export function ScoreGauge({ score, size = 64, indeterminate = false }: Props) {
  const stroke = Math.max(4, Math.round(size / 14));
  const radius = size / 2 - stroke;
  const circumference = 2 * Math.PI * radius;
  const dash = indeterminate ? 0 : (score / 100) * circumference;
  const id = `gauge-${score}-${size}-${indeterminate ? 'i' : 'n'}`;
  const stops = indeterminate
    ? ['#5A6472', '#778190']
    : score >= 85
      ? ['#10B981', '#34D399']
      : score >= 60
        ? ['#F59E0B', '#FBBF24']
        : ['#EF4444', '#F97373'];

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className="drop-shadow-[0_4px_24px_rgba(47,123,255,0.15)]"
    >
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0%" stopColor={stops[0]} />
          <stop offset="100%" stopColor={stops[1]} />
        </linearGradient>
      </defs>
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke="rgb(var(--border))"
        strokeWidth={stroke}
      />
      <circle
        cx={size / 2}
        cy={size / 2}
        r={radius}
        fill="none"
        stroke={`url(#${id})`}
        strokeWidth={stroke}
        strokeDasharray={`${dash} ${circumference}`}
        strokeLinecap="round"
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
        style={{
          transition: 'stroke-dasharray 600ms cubic-bezier(0.22,1,0.36,1)',
        }}
      />
      <text
        x={size / 2}
        y={size / 2 + size / 14}
        textAnchor="middle"
        fontSize={size / 3.4}
        fontWeight={600}
        fill="rgb(var(--text-primary))"
        fontFamily="var(--font-inter), Inter, sans-serif"
      >
        {indeterminate ? '—' : score}
      </text>
      <text
        x={size / 2}
        y={size / 2 + size / 3.6}
        textAnchor="middle"
        fontSize={size / 9.5}
        fontWeight={500}
        fill="rgb(var(--text-muted))"
        letterSpacing="0.18em"
      >
        SCORE
      </text>
    </svg>
  );
}
