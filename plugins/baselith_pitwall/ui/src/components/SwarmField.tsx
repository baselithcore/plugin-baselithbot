import { useTranslation } from 'react-i18next';
import { Network } from 'lucide-react';
import { Panel, Meter } from './ui';

type MeterTone = 'ember' | 'info' | 'go' | 'caution' | 'danger' | 'violet';

const SIGNALS: { key: string; tone: MeterTone }[] = [
  { key: 'pit_pressure', tone: 'danger' },
  { key: 'thermal_risk', tone: 'caution' },
  { key: 'undercut', tone: 'info' },
  { key: 'conserve', tone: 'go' },
];

// Visualises the latest pheromone field deposited by the vertical swarm.
export function SwarmField({ signals }: { signals: Record<string, number> }) {
  const { t } = useTranslation();
  return (
    <Panel
      title={t('swarmField')}
      eyebrow={t('swarmEyebrow')}
      icon={<Network size={16} />}
      tone="info"
    >
      <div className="space-y-3">
        {SIGNALS.map(({ key, tone }) => {
          const v = signals[key] ?? 0;
          return <Meter key={key} label={t(key)} pct={v / 5} tone={tone} readout={v.toFixed(2)} />;
        })}
      </div>
    </Panel>
  );
}
