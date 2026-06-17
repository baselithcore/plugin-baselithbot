import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Flag, CloudRain, Droplets } from 'lucide-react';
import { api } from '../api';
import type { RaceControlStatus } from '../types';
import { Panel } from './ui';

const FLAGS: { status: RaceControlStatus; key: string; on: string }[] = [
  { status: 'green', key: 'rc_green', on: 'border-go/50 bg-go/15 text-go' },
  { status: 'vsc', key: 'rc_vsc', on: 'border-caution/50 bg-caution/15 text-caution' },
  { status: 'safety_car', key: 'rc_safety_car', on: 'border-danger/50 bg-danger/15 text-danger' },
];

function Slider({
  label,
  icon,
  value,
  onChange,
}: {
  label: string;
  icon: React.ReactNode;
  value: number;
  onChange: (v: number) => void;
}) {
  return (
    <label className="block">
      <div className="mb-1.5 flex items-center justify-between text-xs text-dim">
        <span className="flex items-center gap-1.5">
          {icon}
          {label}
        </span>
        <span className="tabular text-ink">{(value * 100).toFixed(0)}%</span>
      </div>
      <input
        type="range"
        min={0}
        max={1}
        step={0.05}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="w-full"
      />
    </label>
  );
}

// Operator controls: inject race-control flags and live weather into the engine.
export function RaceControlPanel() {
  const { t } = useTranslation();
  const [active, setActive] = useState<RaceControlStatus>('green');
  const [wetness, setWetness] = useState(0);
  const [rain, setRain] = useState(0);

  const flag = (status: RaceControlStatus) => {
    setActive(status);
    void api.setRaceControl(status);
  };
  const weather = (w: number, r: number) => {
    setWetness(w);
    setRain(r);
    void api.setWeather(w, r);
  };

  return (
    <Panel title={t('raceControl')} eyebrow={t('operator')} icon={<Flag size={16} />} tone="ember">
      <div className="space-y-4">
        <div className="grid grid-cols-3 gap-2">
          {FLAGS.map((f) => (
            <button
              key={f.status}
              onClick={() => flag(f.status)}
              className={`rounded-lg border px-2 py-2 text-xs font-semibold transition ${
                active === f.status
                  ? f.on
                  : 'border-hair text-faint hover:border-hair-strong hover:text-dim'
              }`}
            >
              {t(f.key)}
            </button>
          ))}
        </div>
        <div className="space-y-3 border-t border-hair pt-3">
          <Slider
            label={t('wetness')}
            icon={<Droplets size={13} className="text-info" />}
            value={wetness}
            onChange={(w) => weather(w, rain)}
          />
          <Slider
            label={t('rain')}
            icon={<CloudRain size={13} className="text-info" />}
            value={rain}
            onChange={(r) => weather(wetness, r)}
          />
        </div>
      </div>
    </Panel>
  );
}
