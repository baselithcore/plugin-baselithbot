import { useTranslation } from 'react-i18next';
import { Layers } from 'lucide-react';
import type { PluginStatus, WidgetSpec } from '@/types';
import { DeclarativeWidget } from '@/components/widgets/DeclarativeWidget';
import { CoreTelemetry } from '@/components/widgets/CoreTelemetry';
import { Sparkline } from '@/components/widgets/Sparkline';

interface Props {
  status: PluginStatus | null;
  widget: WidgetSpec | null;
  latencyHistory: number[];
}

// Full-width operational pane. The old layout wedged 2-3 metrics into a narrow
// column leaving two-thirds of the page empty; here telemetry spans the row and
// the latency trend gets a proper chart instead of a thumbnail.
export function TelemetryTab({ status, widget, latencyHistory }: Props) {
  const { t } = useTranslation();
  const hasMetrics = !!status && status.metrics.length > 0;

  if (!widget && !hasMetrics) {
    return (
      <div className="glass flex flex-col items-center justify-center px-6 py-16 text-center">
        <span className="mb-3 flex h-11 w-11 items-center justify-center rounded-lg surf t-dim">
          <Layers className="h-5 w-5" />
        </span>
        <h3 className="text-[13px] font-semibold t-primary">{t('detail.no_widget_title')}</h3>
        <p className="mt-1.5 max-w-sm text-[12px] leading-relaxed t-dim">
          {t('detail.no_widget_body')}
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
      {widget ? (
        <DeclarativeWidget spec={widget} />
      ) : (
        status && <CoreTelemetry metrics={status.metrics} />
      )}

      <div className="glass flex flex-col gap-3 p-5">
        <div className="flex items-center justify-between text-[11px] font-semibold uppercase tracking-wider t-faint">
          <span>{t('detail.latency_chart')}</span>
          {latencyHistory.length > 0 && (
            <span className="font-mono text-xs font-semibold tabular-nums t-primary">
              {latencyHistory[latencyHistory.length - 1]} ms
            </span>
          )}
        </div>
        {latencyHistory.length >= 2 ? (
          <div className="rounded-lg border brd bg-[var(--surface-inset)] p-3">
            <Sparkline data={latencyHistory} height={120} id="detail-latency-chart" />
          </div>
        ) : (
          <div className="flex flex-1 items-center justify-center rounded-lg border brd bg-[var(--surface-inset)] p-6 text-center text-[12px] t-faint">
            {t('detail.latency_collecting')}
          </div>
        )}
      </div>
    </div>
  );
}
