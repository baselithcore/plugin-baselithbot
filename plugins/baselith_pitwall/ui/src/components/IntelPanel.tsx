import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Brain, Network, Sparkles } from 'lucide-react';
import { api } from '../api';
import type { FusedIndicator, IndicatorSet } from '../types';
import { Panel, Meter, Badge } from './ui';
import { SEVERITY_TONE } from '../lib/race';

const METER_TONE: Record<string, 'go' | 'info' | 'caution' | 'danger'> = {
  low: 'info',
  medium: 'info',
  high: 'caution',
  critical: 'danger',
};

function Indicator({ ind }: { ind: FusedIndicator }) {
  const { t } = useTranslation();
  return (
    <div className="rounded-xl border border-hair bg-surface-2/60 p-3">
      <div className="mb-2 flex items-center justify-between gap-2">
        <span className="text-sm font-semibold text-ink">{ind.label}</span>
        <Badge tone={SEVERITY_TONE[ind.severity]}>{ind.severity}</Badge>
      </div>
      <Meter
        label={ind.rationale}
        pct={ind.value}
        tone={METER_TONE[ind.severity]}
        readout={`${(ind.value * 100).toFixed(0)}%`}
      />
      <div className="mt-2 flex flex-wrap items-center gap-1">
        <Network size={11} className="text-info" />
        {ind.provenance.sources.map((s) => (
          <span key={s} className="tabular rounded bg-surface-3 px-1.5 py-0.5 text-[10px] text-dim">
            {s}
          </span>
        ))}
        <span className="tabular ml-auto text-[10px] text-faint">
          {t('confidence')} {(ind.confidence * 100).toFixed(0)}% · {t('agreement')}{' '}
          {(ind.provenance.agreement * 100).toFixed(0)}%
        </span>
      </div>
    </div>
  );
}

// Palantir-style panel: cross-source fused indicators (with provenance) + AI brief.
export function IntelPanel({ car }: { car: string | null }) {
  const { t } = useTranslation();
  const [set, setSet] = useState<IndicatorSet | null>(null);
  const [brief, setBrief] = useState<string>('');

  useEffect(() => {
    if (!car) return;
    let alive = true;
    const tick = async () => {
      try {
        const s = await api.indicators(car);
        if (alive) setSet(s);
      } catch {
        /* no data */
      }
    };
    void tick();
    const id = setInterval(tick, 2000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [car]);

  useEffect(() => {
    if (!car) return;
    let alive = true;
    const tick = async () => {
      try {
        const r = await api.intel(car);
        if (alive) setBrief(r.brief);
      } catch {
        /* no brief */
      }
    };
    void tick();
    const id = setInterval(tick, 6000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [car]);

  const ranked = set
    ? [...set.indicators].sort((a, b) => b.value * b.confidence - a.value * a.confidence)
    : [];

  return (
    <Panel title={t('intel')} eyebrow={t('fusion')} icon={<Brain size={16} />} tone="caution">
      <div className="space-y-3">
        {brief && (
          <div className="relative overflow-hidden rounded-xl border border-caution/30 bg-caution/[0.06] p-3">
            <div className="mb-1.5 flex items-center gap-1.5 text-caution">
              <Sparkles size={12} />
              <span className="eyebrow text-caution">{t('intelBrief')}</span>
            </div>
            <p className="text-xs leading-relaxed text-ink/90">{brief}</p>
          </div>
        )}
        <div className="eyebrow">{t('fusedIndicators')}</div>
        {ranked.length === 0 ? (
          <p className="py-3 text-center text-sm text-faint">{t('noData')}</p>
        ) : (
          <div className="space-y-2">
            {ranked.map((ind) => (
              <Indicator key={ind.key} ind={ind} />
            ))}
          </div>
        )}
      </div>
    </Panel>
  );
}
