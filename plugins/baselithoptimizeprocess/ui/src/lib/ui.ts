import type { Severity } from '../api/types';

export const SEVERITY_ORDER: Severity[] = ['critical', 'high', 'medium', 'low'];

export const severityRank: Record<Severity, number> = {
  low: 1,
  medium: 2,
  high: 3,
  critical: 4,
};

/** Tailwind text/border/bg classes for a severity chip. */
export const severityChip: Record<Severity, string> = {
  low: 'bg-sev-low/15 text-sev-low border border-sev-low/30',
  medium: 'bg-sev-medium/15 text-sev-medium border border-sev-medium/30',
  high: 'bg-sev-high/15 text-sev-high border border-sev-high/30',
  critical: 'bg-sev-critical/15 text-sev-critical border border-sev-critical/30',
};

/** Hex color used to tint a graph node by its worst bottleneck severity. */
export const severityColor: Record<Severity, string> = {
  low: '#34d399',
  medium: '#fbbf24',
  high: '#fb923c',
  critical: '#f43f5e',
};

const compactNumber = new Intl.NumberFormat(undefined, {
  maximumFractionDigits: 2,
  notation: 'compact',
});

const standardNumber = new Intl.NumberFormat(undefined, {
  maximumFractionDigits: 2,
});

const relativeTime = new Intl.RelativeTimeFormat(undefined, { numeric: 'auto' });

export function formatNumber(value: number, unit = ''): string {
  const formatter = Math.abs(value) >= 10000 ? compactNumber : standardNumber;
  return unit ? `${formatter.format(value)} ${unit}` : formatter.format(value);
}

export function timeAgo(iso: string): string {
  const seconds = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return relativeTime.format(-Math.round(seconds), 'second');
  if (seconds < 3600) return relativeTime.format(-Math.round(seconds / 60), 'minute');
  return relativeTime.format(-Math.round(seconds / 3600), 'hour');
}

export function cn(...parts: (string | false | null | undefined)[]): string {
  return parts.filter(Boolean).join(' ');
}

/** Human-readable duration from seconds (e.g. 90 → "1m 30s", 7200 → "2h"). */
export function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds <= 0) return '0s';
  const units: [number, string][] = [
    [86400, 'd'],
    [3600, 'h'],
    [60, 'm'],
    [1, 's'],
  ];
  const parts: string[] = [];
  let rest = Math.round(seconds);
  for (const [size, label] of units) {
    if (rest >= size) {
      parts.push(`${Math.floor(rest / size)}${label}`);
      rest %= size;
    }
    if (parts.length === 2) break;
  }
  return parts.join(' ') || '0s';
}

/** URL-safe identifier derived from a human label (e.g. "Order Fulfillment" → "order-fulfillment"). */
export function slugify(value: string): string {
  return value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}
