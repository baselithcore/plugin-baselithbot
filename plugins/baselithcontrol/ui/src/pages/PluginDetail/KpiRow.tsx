import { useTranslation } from 'react-i18next';
import { Activity, Clock } from 'lucide-react';
import { asTone, formatValue, relativeTime } from '@/lib/format';
import { Sparkline } from '@/components/widgets/Sparkline';
import type { PluginStatus } from '@/types';
import { StatCard } from './parts/StatCard';

interface Props {
  status: PluginStatus | null;
  latencyHistory: number[];
}

// Always-visible KPI band: latency (with live trend), recency, and the two
// highest-signal core metrics the plugin reports. Replaces the scattered,
// triplicated latency/last-seen chips of the old layout with one scannable row.
export function KpiRow({ status, latencyHistory }: Props) {
  const { t } = useTranslation();
  const extra = (status?.metrics ?? []).slice(0, 2);

  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
      <StatCard
        label={t('detail.latency')}
        value={status?.latency_ms != null ? String(status.latency_ms) : '—'}
        unit="ms"
        icon={<Activity className="h-3.5 w-3.5" />}
      >
        <Sparkline data={latencyHistory} height={28} id="detail-latency" />
      </StatCard>

      <StatCard
        label={t('detail.last_seen')}
        value={relativeTime(status?.last_seen ?? null)}
        icon={<Clock className="h-3.5 w-3.5" />}
      />

      {extra.map((m, i) => (
        <StatCard
          key={i}
          label={m.label}
          value={formatValue(m.value, m.format)}
          tone={asTone(m.tone)}
        />
      ))}
    </div>
  );
}
