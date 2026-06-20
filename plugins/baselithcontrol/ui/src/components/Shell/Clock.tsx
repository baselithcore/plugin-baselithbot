import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Clock as ClockIcon } from 'lucide-react';

// Live wall-clock for the operator. Local time + short date in the browser's
// zone — "when did I see this" only means anything in the operator's own zone;
// the full UTC timestamp is exposed in the tooltip for cross-zone correlation.
// Locale-aware via Intl + the active i18n language (24h, the ops convention).
export function Clock() {
  const { i18n } = useTranslation();
  const [now, setNow] = useState(() => new Date());

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  const locale = i18n.language.startsWith('it') ? 'it-IT' : 'en-US';
  const time = new Intl.DateTimeFormat(locale, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(now);
  const date = new Intl.DateTimeFormat(locale, { day: '2-digit', month: 'short' }).format(now);
  const zone =
    new Intl.DateTimeFormat(locale, { timeZoneName: 'short' })
      .formatToParts(now)
      .find((p) => p.type === 'timeZoneName')?.value ?? '';

  return (
    <span
      className="hidden items-center gap-2 rounded-lg border brd bg-[var(--surface-inset)] px-2.5 py-1.5 lg:inline-flex"
      title={`${now.toUTCString()}`}
    >
      <ClockIcon className="h-3.5 w-3.5 t-faint" />
      <span className="font-mono text-[12px] font-semibold tabular-nums t-primary">{time}</span>
      <span className="text-[11px] font-medium t-faint">
        {date} · {zone}
      </span>
    </span>
  );
}
