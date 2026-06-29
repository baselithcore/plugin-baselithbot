import { useTranslation } from 'react-i18next';
import type { MyLlmUsage, UsageStatus } from '@/types';

export function usd(n: number): string {
  if (n === 0) return '$0';
  if (n < 0.01) return `$${n.toFixed(4)}`;
  return `$${n.toFixed(2)}`;
}

// Localized "June 2026" from the ISO month-start the API returns.
function formatPeriod(iso: string, lang: string): string {
  try {
    return new Intl.DateTimeFormat(lang, { month: 'long', year: 'numeric' }).format(new Date(iso));
  } catch {
    return iso;
  }
}

const BAR: Record<UsageStatus, string> = {
  ok: 'bg-[var(--accent)]',
  warning: 'bg-amber-500',
  blocked: 'bg-rose-500',
};
const STATUS_TEXT: Record<UsageStatus, string> = {
  ok: 't-dim',
  warning: 'text-amber-500',
  blocked: 'text-rose-500',
};

/**
 * Month-to-date LLM consumption as a 0–100% bar (spend vs the effective cap
 * served by the auth plugin). Fails open: when cost governance is off or auth is
 * absent, `usage` is null and a quiet note shows. Shared by the compact account
 * dropdown (`sm`) and the full account page (`md`).
 *
 * `moneyless` is the end-user budget view: a quota glance shows only the
 * percentage of the monthly allowance consumed — never raw billed dollars.
 * Absolute spend is an operator concern (the admin System Console cost ledger),
 * so the user-facing surfaces pass `moneyless` and the money figures are hidden.
 */
export function UsageGauge({
  usage,
  loading,
  size = 'md',
  moneyless = false,
}: {
  usage: MyLlmUsage | null;
  loading: boolean;
  size?: 'sm' | 'md';
  moneyless?: boolean;
}) {
  const { t, i18n } = useTranslation();

  if (loading) return <div className="h-10 animate-pulse rounded-md bg-[var(--surface-inset)]" />;
  if (!usage) return <p className="text-[13px] t-dim">{t('usage.untracked')}</p>;

  const capped = usage.percent_used != null && usage.cap_usd != null;
  const status: UsageStatus = usage.status ?? 'ok';
  const pct = capped ? Math.min(100, Math.max(0, usage.percent_used!)) : 0;
  const pctText = size === 'md' ? 'text-3xl' : 'text-2xl';
  const moneyText = size === 'md' ? 'text-2xl' : 'text-xl';

  if (!capped) {
    // No monthly cap → no percentage to show. Money view shows the raw spend;
    // the user budget view shows only the "no cap" note (no dollars).
    return (
      <div className="flex items-baseline justify-between gap-2">
        {moneyless ? (
          <span className="text-[13px] font-medium t-dim">{t('usage.unlimited')}</span>
        ) : (
          <>
            <span className={`font-display ${moneyText} font-bold tabular-nums t-primary`}>
              {usd(usage.spend_usd)}
            </span>
            <span className="text-[12px] font-medium t-dim">{t('usage.unlimited')}</span>
          </>
        )}
      </div>
    );
  }

  return (
    <>
      <div className="mb-2 flex items-baseline justify-between gap-2">
        <span className={`font-display ${pctText} font-bold tabular-nums t-primary`}>
          {usage.percent_used}%
        </span>
        <span className="text-[12px] font-medium tabular-nums t-dim">
          {moneyless ? t('usage.of_budget') : `${usd(usage.spend_usd)} / ${usd(usage.cap_usd!)}`}
        </span>
      </div>
      <div
        className="h-2.5 overflow-hidden rounded-full bg-[var(--surface-inset)]"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <div
          className={`h-full rounded-full transition-all ${BAR[status]}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="mt-2 flex items-center justify-between text-[11px]">
        <span className={STATUS_TEXT[status]}>{t(`usage.status_${status}`)}</span>
        <span className="t-faint">{formatPeriod(usage.period, i18n.language)}</span>
      </div>
    </>
  );
}
