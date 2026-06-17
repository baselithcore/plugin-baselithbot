import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Swords, TrendingUp, Dices } from 'lucide-react';
import { api } from '../api';
import type { BattleForecast, StrategyOutcome } from '../types';
import { Panel, Meter, Badge, Stat } from './ui';

// Monte-Carlo outcome odds + undercut/overcut battle forecast for the car.
export function StrategyPanel({ car }: { car: string | null }) {
  const { t } = useTranslation();
  const [outcome, setOutcome] = useState<StrategyOutcome | null>(null);
  const [battle, setBattle] = useState<BattleForecast | null>(null);

  useEffect(() => {
    if (!car) {
      setOutcome(null);
      setBattle(null);
      return;
    }
    let alive = true;
    const tick = async () => {
      try {
        const o = await api.outcome(car);
        if (alive) setOutcome(o);
      } catch {
        /* no data */
      }
      try {
        const b = await api.battle(car);
        if (alive) setBattle(b);
      } catch {
        if (alive) setBattle(null);
      }
    };
    void tick();
    const id = setInterval(tick, 2000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [car]);

  return (
    <div className="space-y-4">
      <Panel
        title={t('outcome')}
        eyebrow={t('monteCarlo')}
        icon={<TrendingUp size={16} />}
        tone="go"
        actions={
          outcome && (
            <Badge tone="neutral" icon={<Dices size={11} />}>
              {outcome.samples.toLocaleString()}
            </Badge>
          )
        }
      >
        {outcome ? (
          <div className="space-y-3.5">
            <div className="grid grid-cols-2 gap-2">
              <Stat
                label={t('expFinish')}
                value={`P${outcome.expected_finish.toFixed(1)}`}
                tone="info"
              />
              <Stat
                label={t('neutRate')}
                value={`${(outcome.neutralisation_rate * 100).toFixed(0)}`}
                unit="%"
              />
            </div>
            <Meter
              label={t('pWin')}
              pct={outcome.p_win}
              tone="caution"
              readout={`${(outcome.p_win * 100).toFixed(0)}%`}
            />
            <Meter
              label={t('pPodium')}
              pct={outcome.p_podium}
              tone="go"
              readout={`${(outcome.p_podium * 100).toFixed(0)}%`}
            />
            <div className="flex items-center justify-between rounded-lg border border-hair bg-surface-2/60 px-3 py-2">
              <span className="eyebrow">{t('strategy')}</span>
              <span className="tabular text-sm font-semibold text-ink">
                {outcome.best_strategy}
              </span>
            </div>
          </div>
        ) : (
          <p className="py-4 text-center text-sm text-faint">{t('noData')}</p>
        )}
      </Panel>

      <Panel title={t('battle')} eyebrow={t('headToHead')} icon={<Swords size={16} />} tone="info">
        {battle ? (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="tabular text-base font-semibold text-ink">{battle.rival_id}</span>
              <Badge tone="info">{battle.verdict}</Badge>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <Stat
                label={t('undercutDelta')}
                value={battle.undercut_delta_s.toFixed(1)}
                unit="s"
                tone={battle.undercut_delta_s > 0 ? 'go' : 'danger'}
              />
              <Stat
                label={t('strikeIn')}
                value={battle.laps_to_striking_distance ?? '—'}
                unit={battle.laps_to_striking_distance != null ? t('laps') : ''}
              />
            </div>
            <div className="flex justify-between text-xs text-dim">
              <span>{t('closingRate')}</span>
              <span className="tabular text-ink">
                {battle.closing_rate_s_per_lap.toFixed(2)} s/{t('lap').toLowerCase()}
              </span>
            </div>
          </div>
        ) : (
          <p className="py-4 text-center text-xs text-faint">{t('noBattle')}</p>
        )}
      </Panel>
    </div>
  );
}
