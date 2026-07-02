import { useTranslation } from 'react-i18next';
import type { LogEntry, LogLevel } from '@/types';

// Fixed, theme-independent accent per severity (used for the level chip).
const LEVEL_TONE: Record<LogLevel, string> = {
  DEBUG: 't-faint',
  INFO: 't-dim',
  WARNING: 'text-amber-500',
  ERROR: 'text-rose-500',
  CRITICAL: 'text-rose-600',
};

// Format with the active i18n language (same mapping TimelinePanel uses), not
// the browser locale, so times render consistently across the dashboard.
function clock(ts: number, locale: string): string {
  const d = new Date(ts * 1000);
  return d.toLocaleTimeString(locale.startsWith('it') ? 'it-IT' : 'en-US', { hour12: false });
}

export function LogRow({ entry }: { entry: LogEntry }) {
  const { i18n } = useTranslation();
  const tone = LEVEL_TONE[entry.level] ?? 't-dim';
  return (
    <div className="flex items-start gap-3 border-b brd px-3 py-1.5 font-mono text-[12px] leading-relaxed hover:bg-[var(--surface-inset)]">
      <span
        className="shrink-0 tabular-nums t-faint"
        title={new Date(entry.timestamp * 1000).toISOString()}
      >
        {clock(entry.timestamp, i18n.language)}
      </span>
      <span className={`w-16 shrink-0 font-bold uppercase ${tone}`}>{entry.level}</span>
      <span
        className="w-24 shrink-0 truncate rounded bg-[var(--surface-inset)] px-1.5 text-[11px] font-semibold t-dim"
        title={entry.logger}
      >
        {entry.plugin}
      </span>
      <span className="min-w-0 flex-1 whitespace-pre-wrap break-words t-primary">
        {entry.message}
      </span>
    </div>
  );
}
