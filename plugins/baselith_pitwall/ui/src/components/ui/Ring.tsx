type Tone = 'ember' | 'info' | 'go' | 'caution' | 'danger';

const STROKE: Record<Tone, string> = {
  ember: 'stroke-ember',
  info: 'stroke-info',
  go: 'stroke-go',
  caution: 'stroke-caution',
  danger: 'stroke-danger',
};

interface Props {
  /** 0..1 */
  value: number;
  size?: number;
  tone?: Tone;
  label?: string;
}

/** Compact circular gauge for confidence / probability readouts. */
export function Ring({ value, size = 44, tone = 'info', label }: Props) {
  const r = size / 2 - 4;
  const c = 2 * Math.PI * r;
  const pct = Math.min(1, Math.max(0, value));
  return (
    <div className="relative grid place-items-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          className="fill-none stroke-surface-3"
          strokeWidth={4}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          className={`fill-none ${STROKE[tone]} transition-[stroke-dashoffset] duration-500`}
          strokeWidth={4}
          strokeLinecap="round"
          strokeDasharray={c}
          strokeDashoffset={c * (1 - pct)}
        />
      </svg>
      <span className="tabular absolute text-[11px] font-semibold text-ink">
        {label ?? `${Math.round(pct * 100)}`}
      </span>
    </div>
  );
}
