import { useTranslation } from 'react-i18next';
import { Activity } from 'lucide-react';
import { formatValue, type Tone } from '@/lib/format';
import type { MetricView } from '@/types';
import { MetricChip } from './MetricChip';

// Zero-config telemetry panel: every loaded plugin records lifecycle/timing
// metrics in the framework, so the detail view shows live operational signal
// even when the plugin declares no custom widget. Falls back to the caller's
// empty state only when there are genuinely no metrics.
export function CoreTelemetry({ metrics }: { metrics: MetricView[] }) {
  const { t } = useTranslation();
  return (
    <div className="glass flex flex-col gap-3 p-5">
      <div className="flex items-center justify-between gap-3">
        <h4 className="text-[11px] font-semibold uppercase tracking-wider t-faint">
          {t('detail.telemetry_title')}
        </h4>
        <Activity className="h-4 w-4 t-faint" />
      </div>
      <div className="grid grid-cols-2 gap-2">
        {metrics.map((m, i) => (
          <MetricChip
            key={i}
            label={m.label}
            value={formatValue(m.value, m.format)}
            tone={(m.tone as Tone) ?? 'neutral'}
          />
        ))}
      </div>
    </div>
  );
}
