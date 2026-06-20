import { useTranslation } from 'react-i18next';
import { CheckCircle2, AlertTriangle } from 'lucide-react';
import type { PluginCard as Card, SystemResources } from '@/types';
import { formatUptime } from '@/lib/format';

interface Props {
  cards: Card[];
  resources: SystemResources | null;
  // Jump the grid filter to the offending plugins; `critical` = real failures.
  onInspect: (critical: boolean) => void;
}

// Compact at-a-glance health cluster for the page heading. Stays calm and green
// when all is well; turns amber/red and becomes a click-to-filter shortcut to
// the offending plugins when something fails or degrades. Carries framework
// uptime as a slim secondary chip. Deliberately minimal — a single inline row,
// so the plugin grid (not telemetry) owns the page.
export function StatusStrip({ cards, resources, onInspect }: Props) {
  const { t } = useTranslation();

  const failed = cards.filter((c) => c.state === 'failed');
  const degraded = cards.filter((c) => c.state === 'active' && c.healthy === false);
  const attention = failed.length + degraded.length;
  const critical = failed.length > 0;
  const tone = attention === 0 ? 'text-emerald-500' : critical ? 'text-rose-500' : 'text-amber-500';
  const uptime = resources?.available !== false ? formatUptime(resources?.uptime_seconds) : null;

  return (
    <div className="flex items-center gap-2.5">
      {attention === 0 ? (
        <span className="inline-flex items-center gap-1.5 text-[12px] font-semibold">
          <CheckCircle2 className={`h-3.5 w-3.5 ${tone}`} />
          <span className={`hidden sm:inline ${tone}`}>{t('strip.operational')}</span>
        </span>
      ) : (
        <button
          type="button"
          onClick={() => onInspect(critical)}
          className={`inline-flex items-center gap-1.5 text-[12px] font-semibold transition hover:opacity-80 ${tone}`}
        >
          <AlertTriangle className="h-3.5 w-3.5" />
          {t('strip.attention', { count: attention })}
        </button>
      )}
      {uptime && (
        <span className="hidden items-center rounded-lg border brd bg-[var(--surface-inset)] px-2 py-1 font-mono text-[11px] tabular-nums t-faint md:inline-flex">
          {t('strip.uptime', { uptime })}
        </span>
      )}
    </div>
  );
}
