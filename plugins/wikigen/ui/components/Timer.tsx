import { Clock, Gauge, Timer as TimerIcon, Zap } from 'lucide-react';
import { useElapsed } from '../hooks/useElapsed';
import { cn } from '../lib/cn';

interface Props {
  startedAt?: number;
  firstTokenAt?: number;
  completedAt?: number;
  streaming?: boolean;
  variant?: 'inline' | 'pill';
}

function fmt(ms: number): string {
  if (ms < 1000) return `${ms} ms`;
  const s = ms / 1000;
  if (s < 10) return `${s.toFixed(2)}s`;
  if (s < 60) return `${s.toFixed(1)}s`;
  const m = Math.floor(s / 60);
  const rem = Math.round(s - m * 60);
  return `${m}m ${rem}s`;
}

/**
 * Badge temporale della risposta:
 *  - durante streaming: tempo live + (se già arrivato) tempo al primo token
 *  - al termine: TTFT + totale
 */
export function Timer({
  startedAt,
  firstTokenAt,
  completedAt,
  streaming,
  variant = 'pill',
}: Props) {
  const total = useElapsed(startedAt, !!streaming, completedAt);
  const ttft = firstTokenAt && startedAt ? firstTokenAt - startedAt : null;

  if (!startedAt) return null;

  const isInline = variant === 'inline';

  return (
    <div
      className={cn(
        'inline-flex items-center gap-2 tabular-nums',
        isInline
          ? 'text-[11px] text-ink-subtle'
          : 'text-[11px] rounded-full px-2 py-0.5 bg-[var(--color-surface)] border border-[var(--color-border)] text-ink-muted'
      )}
      title={
        ttft != null
          ? `primo token dopo ${fmt(ttft)} · generazione totale ${fmt(total)}`
          : `in attesa del primo token · ${fmt(total)}`
      }
    >
      {streaming ? (
        <>
          <TimerIcon size={10} className="text-[var(--color-brand)] animate-pulse" />
          <span>{fmt(total)}</span>
          {ttft != null && (
            <span className="text-ink-subtle">
              · <Zap size={9} className="inline -mt-0.5" /> {fmt(ttft)}
            </span>
          )}
        </>
      ) : (
        <>
          <Clock size={10} className="text-ink-subtle" />
          <span>{fmt(total)}</span>
          {ttft != null && (
            <span className="text-ink-subtle">
              · <Gauge size={9} className="inline -mt-0.5" /> ttft {fmt(ttft)}
            </span>
          )}
        </>
      )}
    </div>
  );
}
