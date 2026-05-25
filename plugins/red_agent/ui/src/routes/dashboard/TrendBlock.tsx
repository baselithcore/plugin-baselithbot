import { Icon } from '../../components/ui';

export function TrendBlock({
  label,
  value,
  color,
  series,
}: {
  label: string;
  value: number;
  color: string;
  series: number[];
}) {
  const last = series[series.length - 1] ?? 0;
  const first = series[0] ?? 0;
  const delta = last - first;
  const dir = delta > 0 ? 'up' : delta < 0 ? 'down' : 'flat';
  return (
    <div className="rounded-md border border-bg-line bg-bg-elevated/60 px-3 py-2">
      <div className="flex items-center justify-between">
        <span className="text-2xs font-mono uppercase tracking-wider" style={{ color }}>
          {label}
        </span>
        <span
          className={`inline-flex items-center gap-0.5 text-2xs font-mono ${
            dir === 'up'
              ? 'text-sev-critical'
              : dir === 'down'
                ? 'text-status-success'
                : 'text-text-muted'
          }`}
        >
          {dir === 'up' && <Icon.ArrowUp size={10} />}
          {dir === 'down' && <Icon.ArrowDown size={10} />}
          {Math.abs(delta) || '—'}
        </span>
      </div>
      <div className="font-display text-2xl font-medium tabular-nums text-text-primary">
        {value}
      </div>
    </div>
  );
}
