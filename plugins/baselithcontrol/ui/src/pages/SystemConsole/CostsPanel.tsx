import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Info, DollarSign } from 'lucide-react';
import { fetchCostUsage, fetchPricing } from '@/lib/api';
import { formatTokens, formatUsd } from '@/lib/format';
import { usePoll } from '@/hooks/usePoll';
import type { CostUsageView, PricingView } from '@/types';

const POLL_MS = 5000;

export function CostsPanel() {
  const { t } = useTranslation();
  const [usage, setUsage] = useState<CostUsageView | null>(null);
  const [pricing, setPricing] = useState<PricingView | null>(null);
  const [error, setError] = useState<string | null>(null);

  usePoll(
    async (alive) => {
      try {
        const u = await fetchCostUsage();
        if (alive()) {
          setUsage(u);
          setError(null);
        }
        return true;
      } catch (e) {
        if (alive()) setError(e instanceof Error ? e.message : 'failed');
        return false;
      }
    },
    { intervalMs: POLL_MS }
  );

  // Pricing reference is a static snapshot — one fetch on mount suffices.
  useEffect(() => {
    let alive = true;
    fetchPricing()
      .then((p) => alive && setPricing(p))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, []);

  if (error)
    return <div className="glass border-rose-500/25 p-6 text-sm text-rose-500">{error}</div>;
  if (!usage)
    return <div className="glass p-12 text-center text-[13px] t-dim">{t('cost.loading')}</div>;

  const rows = usage.rows;

  return (
    <div className="space-y-5">
      {/* Scope: whose spend these figures cover (own tenant vs all users) */}
      <div className="flex items-center justify-between gap-3">
        <span
          className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-1 text-[11px] font-semibold uppercase tracking-wide ${
            usage.scope === 'global'
              ? 'border-[var(--accent-border)] bg-[var(--accent-soft)] t-accent'
              : 'brd t-dim'
          }`}
        >
          <DollarSign className="h-3.5 w-3.5" />
          {usage.scope === 'global' ? t('cost.scope_global') : t('cost.scope_tenant')}
        </span>
      </div>

      {/* Disclaimer — measured tokens, list-price cost */}
      <div className="flex items-start gap-2.5 rounded-lg border border-[var(--accent-border)] bg-[var(--accent-soft)] p-3 text-[12.5px] t-dim">
        <Info className="mt-0.5 h-4 w-4 shrink-0 t-accent" />
        <p>{t('cost.usage_disclaimer')}</p>
      </div>

      {/* Totals */}
      <div className="glass grid grid-cols-2 gap-px overflow-hidden bg-[var(--border)] sm:grid-cols-3">
        {[
          { label: t('cost.total_spend'), value: formatUsd(usage.total_cost_usd), accent: true },
          { label: t('cost.total_tokens'), value: formatTokens(usage.total_tokens) },
          {
            label: t('cost.tracked_plugins'),
            value: String(new Set(rows.map((r) => r.plugin)).size),
          },
        ].map((kpi) => (
          <div key={kpi.label} className="bg-[var(--surface-1)] p-4">
            <div className="text-[11px] font-medium uppercase tracking-wide t-faint">
              {kpi.label}
            </div>
            <div
              className={`font-display text-2xl font-bold tabular-nums ${kpi.accent ? 't-accent' : 't-primary'}`}
            >
              {kpi.value}
            </div>
          </div>
        ))}
      </div>

      {/* Per-plugin spend table */}
      <div className="glass overflow-hidden">
        <div className="grid grid-cols-[1.4fr_1.4fr_auto_auto_auto] gap-x-3 border-b brd px-4 py-2.5 text-[11px] font-semibold uppercase tracking-wide t-faint">
          <span>{t('cost.col_plugin')}</span>
          <span>{t('cost.col_used_model')}</span>
          <span className="text-right">{t('cost.col_calls')}</span>
          <span className="text-right">{t('cost.col_tokens')}</span>
          <span className="text-right">{t('cost.col_cost')}</span>
        </div>
        {rows.length === 0 ? (
          <div className="flex flex-col items-center gap-2 p-12 text-center">
            <DollarSign className="h-6 w-6 t-faint" />
            <p className="text-[13px] t-dim">{t('cost.empty')}</p>
          </div>
        ) : (
          rows.map((r) => (
            <div
              key={`${r.plugin}:${r.model}`}
              className="grid grid-cols-[1.4fr_1.4fr_auto_auto_auto] items-center gap-x-3 border-b brd px-4 py-2 text-[13px] last:border-0 hover:bg-[var(--surface-inset)]"
            >
              <span
                className={`truncate font-semibold ${r.plugin === 'unbound' ? 't-faint' : 't-primary'}`}
              >
                {r.plugin}
              </span>
              <span className="truncate font-mono text-[12px] t-dim">{r.model}</span>
              <span className="text-right tabular-nums t-dim">{r.calls}</span>
              <span
                className="text-right tabular-nums t-dim"
                title={`${r.prompt_tokens} in / ${r.completion_tokens} out`}
              >
                {formatTokens(r.total_tokens)}
              </span>
              <span className="text-right font-semibold tabular-nums t-primary">
                {formatUsd(r.cost_usd)}
              </span>
            </div>
          ))
        )}
      </div>

      {/* Pricing reference */}
      {pricing && (
        <details className="glass overflow-hidden">
          <summary className="cursor-pointer px-4 py-3 text-[12px] font-semibold uppercase tracking-wide t-dim">
            {t('cost.reference', { date: pricing.as_of })}
          </summary>
          <div className="grid grid-cols-[1fr_auto_auto] gap-x-4 border-t brd px-4 py-2 text-[11px] font-semibold uppercase tracking-wide t-faint">
            <span>{t('cost.col_model')}</span>
            <span className="text-right">{t('cost.col_input')}</span>
            <span className="text-right">{t('cost.col_output')}</span>
          </div>
          {pricing.rows.map((r) => (
            <div
              key={r.model_id}
              className="grid grid-cols-[1fr_auto_auto] gap-x-4 border-t brd px-4 py-1.5 text-[12.5px]"
            >
              <span className="min-w-0">
                <span className="font-mono t-primary">{r.model_id}</span>
                <span className="ml-2 text-[11px] t-faint">{r.provider}</span>
              </span>
              <span className="text-right tabular-nums t-dim">
                {formatUsd(r.input_usd_per_million)}
              </span>
              <span className="text-right tabular-nums t-dim">
                {formatUsd(r.output_usd_per_million)}
              </span>
            </div>
          ))}
        </details>
      )}
    </div>
  );
}
