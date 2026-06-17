import { useTranslation } from 'react-i18next';
import { Cpu, Radio } from 'lucide-react';
import type { Status } from '../../types';

function Chip({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="flex items-baseline gap-1.5 whitespace-nowrap">
      <span className="eyebrow leading-none">{label}</span>
      <span className="tabular text-sm font-semibold text-ink">{value}</span>
    </div>
  );
}

/** Always-on live telemetry readout shown in the top HUD. */
export function TelemetryStrip({ status }: { status: Status | null }) {
  const { t } = useTranslation();
  const running = status?.running ?? false;
  return (
    <div className="scroll-slim flex items-center gap-4 overflow-x-auto">
      <div
        className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 ${
          running ? 'border-go/40 bg-go/10' : 'border-hair bg-surface-2'
        }`}
      >
        <span className={`h-1.5 w-1.5 rounded-full ${running ? 'bg-go pulse-dot' : 'bg-faint'}`} />
        <span
          className={`text-[11px] font-semibold uppercase tracking-wider ${running ? 'text-go' : 'text-faint'}`}
        >
          {running ? t('live') : t('standby')}
        </span>
      </div>
      <span className="h-5 w-px bg-hair" />
      <Chip label={t('cars')} value={status?.cars_tracked ?? 0} />
      <Chip label={t('frames')} value={status?.frames_ingested ?? 0} />
      <Chip label={t('recommendations')} value={status?.recommendations_emitted ?? 0} />
      <Chip label={t('queue')} value={status?.queue_depth ?? 0} />
      <Chip label={t('agents')} value={status?.swarm_agents ?? 0} />
      <span className="h-5 w-px bg-hair" />
      <div className="flex items-center gap-2">
        <Cpu
          size={14}
          className={status?.llm_enabled ? 'text-caution' : 'text-faint'}
          aria-label="LLM"
        />
        <Radio
          size={14}
          className={status?.semantic_enabled ? 'text-info' : 'text-faint'}
          aria-label="Semantic"
        />
      </div>
    </div>
  );
}
