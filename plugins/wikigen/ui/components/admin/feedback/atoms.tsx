/**
 * Atoms condivisi della sezione admin feedback.
 *
 * - ``StatCard``: KPI card per il pannello dashboard.
 * - ``RatingPill``: badge up/down con icona + colore tematico.
 * - ``Sparkline``: SVG inline minimale (no recharts dep) per trend up/down.
 */

import { ThumbsDown, ThumbsUp } from 'lucide-react';
import type { ReactNode } from 'react';

import { cn } from '../../../lib/cn';

export function StatCard({
  label,
  value,
  hint,
  tone = 'neutral',
  icon,
}: {
  label: string;
  value: ReactNode;
  hint?: ReactNode;
  tone?: 'neutral' | 'success' | 'danger' | 'brand';
  icon?: ReactNode;
}) {
  const toneRing =
    tone === 'success'
      ? 'ring-emerald-500/15'
      : tone === 'danger'
        ? 'ring-rose-500/15'
        : tone === 'brand'
          ? 'ring-[var(--color-brand-soft)]'
          : 'ring-[var(--color-border)]';
  const toneText =
    tone === 'success'
      ? 'text-emerald-600 dark:text-emerald-400'
      : tone === 'danger'
        ? 'text-rose-600 dark:text-rose-400'
        : tone === 'brand'
          ? 'text-[var(--color-brand-contrast)]'
          : 'text-ink';
  return (
    <div
      className={cn(
        'flex flex-col gap-1 rounded-lg bg-[var(--color-surface)] p-4 ring-1',
        toneRing
      )}
    >
      <div className="flex items-center justify-between">
        <span className="text-[10px] uppercase tracking-wide text-ink-subtle">{label}</span>
        {icon && <span className={cn('opacity-70', toneText)}>{icon}</span>}
      </div>
      <span className={cn('text-2xl font-semibold leading-tight', toneText)}>{value}</span>
      {hint && <span className="text-[11px] text-ink-subtle leading-snug">{hint}</span>}
    </div>
  );
}

export function RatingPill({ rating }: { rating: 'up' | 'down' }) {
  if (rating === 'up') {
    return (
      <span className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium bg-emerald-500/10 text-emerald-700 dark:text-emerald-400">
        <ThumbsUp size={11} />
        Positivo
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium bg-rose-500/10 text-rose-700 dark:text-rose-400">
      <ThumbsDown size={11} />
      Negativo
    </span>
  );
}

/**
 * Sparkline dual-series (up/down) — SVG inline, niente dep.
 * Layout: due polyline normalizzate sull'altezza, sfondo trasparente.
 */
export function Sparkline({
  series,
  width = 220,
  height = 44,
}: {
  series: Array<{ bucket: string; up: number; down: number }>;
  width?: number;
  height?: number;
}) {
  if (series.length === 0) {
    return (
      <div
        className="flex items-center justify-center rounded bg-[var(--color-surface)] text-[10px] text-ink-subtle"
        style={{ width, height }}
      >
        nessun dato nel periodo
      </div>
    );
  }
  const maxVal = Math.max(1, ...series.map((s) => Math.max(s.up, s.down)));
  const pad = 4;
  const innerW = width - pad * 2;
  const innerH = height - pad * 2;
  const stepX = series.length > 1 ? innerW / (series.length - 1) : 0;
  const pointsFor = (key: 'up' | 'down'): string =>
    series
      .map((s, i) => {
        const x = pad + stepX * i;
        const y = pad + innerH - (s[key] / maxVal) * innerH;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(' ');
  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={`trend feedback (${series.length} bucket)`}
    >
      <polyline
        points={pointsFor('up')}
        fill="none"
        stroke="rgb(16 185 129)"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <polyline
        points={pointsFor('down')}
        fill="none"
        stroke="rgb(244 63 94)"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

export function PercentBar({ pct }: { pct: number }) {
  const value = Math.max(0, Math.min(1, pct));
  const pctLabel = `${Math.round(value * 100)}%`;
  return (
    <div className="flex items-center gap-2" title={pctLabel}>
      <div className="relative h-1.5 flex-1 overflow-hidden rounded-full bg-rose-500/15">
        <div className="h-full rounded-full bg-emerald-500/80" style={{ width: pctLabel }} />
      </div>
      <span className="w-10 shrink-0 text-right text-[10px] font-medium tabular-nums text-ink-subtle">
        {pctLabel}
      </span>
    </div>
  );
}
