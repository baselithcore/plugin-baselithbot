import { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { useTranslation } from 'react-i18next';
import { fetchPluginStatus, fetchWidgets } from '@/lib/api';
import { relativeTime } from '@/lib/format';
import { usePoll } from '@/hooks/usePoll';
import { safeInternalUrl } from '@/lib/url';
import { useControlStore } from '@/store/useControlStore';
import { pageVariants } from '@/lib/motion';
import type { PluginStatus, WidgetSpec } from '@/types';
import { Header } from './Header';
import { KpiRow } from './KpiRow';
import { OverviewTab } from './OverviewTab';
import { TelemetryTab } from './TelemetryTab';

type Tab = 'overview' | 'telemetry';
const TABS: Tab[] = ['overview', 'telemetry'];

// Stable empty-array reference: a `?? []` literal inside the zustand selector
// would mint a new array every render, so the Object.is check always fails →
// re-render → infinite loop ("Maximum update depth exceeded") → blank screen.
const EMPTY_HISTORY: number[] = [];

export function PluginDetail({ name, onBack }: { name: string; onBack: () => void }) {
  const { t } = useTranslation();
  const card = useControlStore((s) => s.plugins[name]);
  const me = useControlStore((s) => s.me);
  const latencyHistory = useControlStore((s) => s.latencyHistory[name]) ?? EMPTY_HISTORY;

  const [tab, setTab] = useState<Tab>('overview');
  const [status, setStatus] = useState<PluginStatus | null>(null);
  const [widget, setWidget] = useState<WidgetSpec | null>(null);

  useEffect(() => {
    let alive = true;
    void fetchWidgets()
      .then((ws) => alive && setWidget(ws.find((w) => w.plugin === name) ?? null))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [name]);

  usePoll(
    async (alive) => {
      try {
        const s = await fetchPluginStatus(name);
        if (alive()) {
          setStatus(s);
          if (typeof s.latency_ms === 'number') {
            useControlStore.getState().addLatency(name, s.latency_ms);
          }
        }
        return true;
      } catch {
        return false; // status is best-effort; backoff covers persistent errors
      }
    },
    { intervalMs: 4000, key: name }
  );

  if (!card) return null;

  const surface = card.surfaces.find((s) => s.embeddable && s.mount_url);
  const launchUrl = safeInternalUrl(surface?.mount_url);
  const canControl = me?.is_admin ?? false;
  const healthTip = status
    ? `${t('detail.latency')}: ${status.latency_ms ?? '—'}ms · ${t('detail.last_seen')}: ${relativeTime(status.last_seen)}`
    : undefined;

  return (
    <motion.div
      variants={pageVariants}
      initial="hidden"
      animate="show"
      exit="exit"
      className="flex flex-col gap-5"
    >
      <Header
        card={card}
        launchUrl={launchUrl}
        canControl={canControl}
        healthTip={healthTip}
        onBack={onBack}
      />

      <KpiRow status={status} latencyHistory={latencyHistory} />

      <div className="flex w-fit gap-1 rounded-lg border brd bg-[var(--surface-inset)] p-0.5">
        {TABS.map((tk) => (
          <button
            key={tk}
            type="button"
            onClick={() => setTab(tk)}
            className={`rounded-md px-3.5 py-1.5 text-[12px] font-medium transition ${
              tab === tk ? 'bg-[var(--accent-soft)] t-accent' : 't-dim hover:text-[var(--text)]'
            }`}
          >
            {t(`detail.${tk}`)}
          </button>
        ))}
      </div>

      {tab === 'overview' ? (
        <OverviewTab card={card} surfaceLabel={surface?.label ?? '—'} canControl={canControl} />
      ) : (
        <TelemetryTab status={status} widget={widget} latencyHistory={latencyHistory} />
      )}
    </motion.div>
  );
}
