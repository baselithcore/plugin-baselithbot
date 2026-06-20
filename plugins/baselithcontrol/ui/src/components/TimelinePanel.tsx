import { useTranslation } from 'react-i18next';
import {
  History,
  Activity,
  CheckCircle2,
  XCircle,
  RotateCw,
  PowerOff,
  Zap,
  type LucideIcon,
} from 'lucide-react';
import { useTimeline } from '@/hooks/useTimeline';

// Map each retained lifecycle topic to an icon, tone and i18n label.
const META: Record<string, { icon: LucideIcon; tone: string; key: string }> = {
  'plugin.activated': { icon: CheckCircle2, tone: 'text-emerald-500', key: 'timeline.activated' },
  'plugin.deactivated': { icon: PowerOff, tone: 'text-amber-500', key: 'timeline.deactivated' },
  'plugin.reloaded': { icon: RotateCw, tone: 'text-sky-500', key: 'timeline.reloaded' },
  'plugin.failed': { icon: XCircle, tone: 'text-rose-500', key: 'timeline.failed' },
  'baselithcontrol.action': { icon: Zap, tone: 'text-[var(--accent)]', key: 'timeline.action' },
};

function formatTime(epochSeconds: number, locale: string): string {
  return new Intl.DateTimeFormat(locale, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(new Date(epochSeconds * 1000));
}

// Recent-activity timeline: the server-retained lifecycle history (activations,
// failures, reloads, governed actions). Complements the live Events feed — this
// one survives reloads and answers "what changed recently?" at a glance.
export function TimelinePanel() {
  const { t, i18n } = useTranslation();
  const { events } = useTimeline(12);
  const locale = i18n.language.startsWith('it') ? 'it-IT' : 'en-US';

  return (
    <section className="glass overflow-hidden">
      <div className="flex items-center gap-2 border-b brd px-4 py-2.5">
        <History className="h-3.5 w-3.5 t-faint" />
        <h3 className="text-[12px] font-semibold uppercase tracking-wide t-dim">
          {t('timeline.title')}
        </h3>
      </div>

      {events.length === 0 ? (
        <p className="px-4 py-6 text-center text-[12px] t-faint">{t('timeline.empty')}</p>
      ) : (
        <ul className="divide-y divide-[var(--border)]">
          {events.map((e, i) => {
            const meta = META[e.type];
            const Icon = meta?.icon ?? Activity;
            const tone = meta?.tone ?? 't-faint';
            return (
              <li key={`${e.timestamp}-${i}`} className="flex items-center gap-3 px-4 py-2">
                <Icon className={`h-3.5 w-3.5 shrink-0 ${tone}`} />
                <span className={`shrink-0 text-[12px] font-semibold ${tone}`}>
                  {meta ? t(meta.key) : e.type}
                </span>
                {e.plugin && (
                  <span className="truncate font-mono text-[12px] t-primary">{e.plugin}</span>
                )}
                <span className="ml-auto shrink-0 font-mono text-[11px] tabular-nums t-faint">
                  {formatTime(e.timestamp, locale)}
                </span>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
