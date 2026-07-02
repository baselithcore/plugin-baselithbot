// Value formatting + dot-path extraction for declarative widgets (the
// customapi-style escape hatch). Mirrors Homepage's `format` vocabulary.

import i18n from '@/i18n';

export type Tone = 'neutral' | 'success' | 'warning' | 'danger' | 'info';

// Validated tone lookup — plugin-reported metric tones are free-form strings,
// so coerce them through a map with a neutral fallback instead of casting.
const TONE_LOOKUP: Record<string, Tone> = {
  neutral: 'neutral',
  success: 'success',
  warning: 'warning',
  danger: 'danger',
  info: 'info',
};

/** Coerce a free-form tone string to a known {@link Tone} (neutral fallback). */
export function asTone(value: string | null | undefined): Tone {
  return TONE_LOOKUP[value ?? ''] ?? 'neutral';
}

export function getByPath(obj: unknown, path: string): unknown {
  return path.split('.').reduce<unknown>((acc, key) => {
    if (acc == null) return undefined;
    if (Array.isArray(acc)) return acc[Number(key)];
    if (typeof acc === 'object') return (acc as Record<string, unknown>)[key];
    return undefined;
  }, obj);
}

function asNumber(value: unknown): number | null {
  const n = typeof value === 'number' ? value : Number(value);
  return Number.isFinite(n) ? n : null;
}

export function formatValue(value: unknown, format: string): string {
  if (value == null) return '—';
  switch (format) {
    case 'percent': {
      const n = asNumber(value);
      return n == null ? String(value) : `${n.toLocaleString()}%`;
    }
    case 'bytes': {
      const n = asNumber(value);
      if (n == null) return String(value);
      const units = ['B', 'KB', 'MB', 'GB', 'TB'];
      let v = n;
      let i = 0;
      while (v >= 1024 && i < units.length - 1) {
        v /= 1024;
        i += 1;
      }
      return `${v.toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
    }
    case 'duration': {
      const ms = asNumber(value);
      if (ms == null) return String(value);
      if (ms < 1000) return `${Math.round(ms)}ms`;
      const s = ms / 1000;
      if (s < 60) return `${s.toFixed(1)}s`;
      const m = Math.floor(s / 60);
      return `${m}m ${Math.round(s % 60)}s`;
    }
    case 'number': {
      const n = asNumber(value);
      return n == null ? String(value) : n.toLocaleString();
    }
    default:
      return String(value);
  }
}

// Conditional coloring: { gte | lte | eq: x, tone: "warning" }.
export function highlightTone(value: unknown, highlight: Record<string, unknown> | null): Tone {
  if (!highlight) return 'neutral';
  const tone = (highlight.tone as Tone) ?? 'info';
  const n = asNumber(value);
  if (n == null) return 'neutral';
  if (typeof highlight.gte === 'number' && n >= highlight.gte) return tone;
  if (typeof highlight.lte === 'number' && n <= highlight.lte) return tone;
  if (typeof highlight.eq === 'number' && n === highlight.eq) return tone;
  return 'neutral';
}

export function formatBytes(value: number | null | undefined): string {
  if (value == null) return '—';
  return formatValue(value, 'bytes');
}

export function formatRate(bytesPerSec: number | null | undefined): string {
  if (bytesPerSec == null) return '—';
  return `${formatValue(bytesPerSec, 'bytes')}/s`;
}

export function formatUptime(seconds: number | null | undefined): string {
  if (seconds == null) return '—';
  const s = Math.floor(seconds);
  const d = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  const m = Math.floor((s % 3600) / 60);
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s % 60}s`;
  return `${s}s`;
}

// Compact USD for LLM spend: keep small amounts legible (4dp) without noise.
export function formatUsd(value: number | null | undefined): string {
  if (value == null) return '—';
  if (value === 0) return '$0';
  if (value < 0.01) return `$${value.toFixed(4)}`;
  return `$${value.toFixed(2)}`;
}

// Compact token counts: 1234 → "1.2k", 2_500_000 → "2.5M".
export function formatTokens(value: number | null | undefined): string {
  if (value == null) return '—';
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1000) return `${(value / 1000).toFixed(1)}k`;
  return String(value);
}

// Localized via the active i18n language (catalog keys under `time.*`).
export function relativeTime(epochSeconds: number | null): string {
  if (epochSeconds == null) return '—';
  const delta = Math.max(0, Date.now() / 1000 - epochSeconds);
  if (delta < 60) return i18n.t('time.s_ago', { n: Math.round(delta) });
  if (delta < 3600) return i18n.t('time.m_ago', { n: Math.round(delta / 60) });
  return i18n.t('time.h_ago', { n: Math.round(delta / 3600) });
}
