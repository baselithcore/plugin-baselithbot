type Tone = 'ember' | 'info' | 'go' | 'caution' | 'danger' | 'violet';

const FILL: Record<Tone, string> = {
  ember: 'bg-ember',
  info: 'bg-info',
  go: 'bg-go',
  caution: 'bg-caution',
  danger: 'bg-danger',
  violet: 'bg-violet',
};

interface Props {
  label: string;
  /** Normalised 0..1 fill. */
  pct: number;
  tone?: Tone;
  /** Right-aligned formatted readout (e.g. "62%", "1.2s"). */
  readout?: string;
}

/** Labelled horizontal meter with an animated fill. */
export function Meter({ label, pct, tone = 'info', readout }: Props) {
  const w = Math.min(100, Math.max(0, pct * 100));
  return (
    <div>
      <div className="mb-1 flex items-baseline justify-between gap-2">
        <span className="truncate text-xs text-dim">{label}</span>
        {readout != null && <span className="tabular text-xs text-ink">{readout}</span>}
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-surface-3">
        <div
          className={`h-full rounded-full ${FILL[tone]} transition-[width] duration-500 ease-out`}
          style={{ width: `${w}%` }}
        />
      </div>
    </div>
  );
}
