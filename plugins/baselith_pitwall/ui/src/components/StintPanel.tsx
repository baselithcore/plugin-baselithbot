import { useTranslation } from 'react-i18next';
import { Gauge, Play, Loader2, Sparkles } from 'lucide-react';
import type { Scenario, Stint } from '../types';
import { Panel, Stat, Meter, Badge } from './ui';
import { compoundStyle, wearTone } from '../lib/race';

interface Props {
  stint: Stint | null;
  scenario: Scenario | null;
  onSimulate: () => void;
  busy: boolean;
}

export function StintPanel({ stint, scenario, onSimulate, busy }: Props) {
  const { t } = useTranslation();

  if (!stint) {
    return (
      <Panel title={t('stintTitle')} eyebrow={t('carCard')} icon={<Gauge size={16} />}>
        <p className="py-6 text-center text-sm text-faint">{t('selectCar')}</p>
      </Panel>
    );
  }

  const comp = compoundStyle(stint.compound);

  return (
    <Panel
      title={stint.car_id}
      eyebrow={t('carCard')}
      icon={<Gauge size={16} />}
      tone="ember"
      actions={
        <span className="tabular text-sm text-dim">
          {t('lap')} <span className="text-ink">{stint.lap}</span>/{stint.total_laps}
        </span>
      }
    >
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-baseline gap-2">
            <span className="font-display text-3xl font-bold leading-none text-ink">
              P{stint.position}
            </span>
            <span className="eyebrow">{t('position')}</span>
          </div>
          <Badge tone={comp.tone}>
            <span className="tabular font-bold">{comp.letter}</span>
            {stint.compound} · {stint.tyre_age_laps} {t('laps')}
          </Badge>
        </div>

        <Meter
          label={`${t('wear')} · ${t('deg')} ${(stint.deg_rate_per_lap * 100).toFixed(1)}%`}
          pct={stint.tyre_wear}
          tone={wearTone(stint.tyre_wear)}
          readout={`${(stint.tyre_wear * 100).toFixed(0)}%`}
        />

        <div className="grid grid-cols-3 gap-2">
          <Stat label={t('fuel')} value={stint.fuel_kg.toFixed(1)} unit="kg" />
          <Stat
            label={t('engineTemp')}
            value={stint.engine_temp_c.toFixed(0)}
            unit="°C"
            tone={stint.engine_temp_c > 120 ? 'danger' : 'ink'}
          />
          <Stat
            label={t('gapAhead')}
            value={stint.gap_ahead_s != null ? stint.gap_ahead_s.toFixed(1) : '—'}
            unit={stint.gap_ahead_s != null ? 's' : ''}
          />
        </div>

        <button
          onClick={onSimulate}
          disabled={busy}
          className="flex w-full items-center justify-center gap-2 rounded-lg border border-info/40 bg-info/10 py-2.5 text-sm font-semibold text-info transition hover:bg-info/20 disabled:opacity-50"
        >
          {busy ? <Loader2 size={15} className="animate-spin" /> : <Play size={15} />}
          {t('simulate')}
        </button>

        {scenario && (
          <div className="rounded-xl border border-hair bg-surface-2/60 p-3">
            <div className="mb-2 flex items-center justify-between">
              <span className="eyebrow flex items-center gap-1 text-info">
                <Sparkles size={11} /> {t('scenario')}
              </span>
              <span className="tabular text-xs text-go">
                {t('expPos')} P{scenario.expected_position.toFixed(1)} ·{' '}
                {(scenario.probability * 100).toFixed(0)}%
              </span>
            </div>
            <div className="flex flex-wrap gap-1">
              {scenario.actions.slice(0, 8).map((a, i) => (
                <span
                  key={i}
                  className="tabular rounded-md bg-surface-3 px-2 py-0.5 text-[11px] text-dim"
                >
                  {a}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </Panel>
  );
}
