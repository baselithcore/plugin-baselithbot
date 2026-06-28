import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Shield, User, LogOut, ChevronDown, Gauge } from 'lucide-react';
import { fetchMyLlmUsage, logout } from '@/lib/api';
import type { Me, MyLlmUsage, UsageStatus } from '@/types';

function usd(n: number): string {
  if (n === 0) return '$0';
  if (n < 0.01) return `$${n.toFixed(4)}`;
  return `$${n.toFixed(2)}`;
}

// Localized "June 2026" from the ISO month-start the API returns.
function formatPeriod(iso: string, lang: string): string {
  try {
    return new Intl.DateTimeFormat(lang, { month: 'long', year: 'numeric' }).format(
      new Date(iso),
    );
  } catch {
    return iso;
  }
}

// Bar fill keyed to the auth cost-status (ok / approaching warn / over cap).
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
 * Top-right identity control. Clicking the name opens a popover with the user's
 * month-to-date LLM consumption as a 0–100% bar (spend vs their effective
 * monthly cap, served by the auth plugin) plus a logout action. Usage fails
 * open: if cost governance is off or auth is absent, the gauge is simply hidden.
 */
export function UserMenu({ me }: { me: Me }) {
  const { t, i18n } = useTranslation();
  const [open, setOpen] = useState(false);
  const [usage, setUsage] = useState<MyLlmUsage | null>(null);
  const [loading, setLoading] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  // Refetch each time the menu opens — cheap, and always shows current spend.
  useEffect(() => {
    if (!open) return;
    let alive = true;
    setLoading(true);
    fetchMyLlmUsage()
      .then((u) => alive && setUsage(u))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [open]);

  // Dismiss on outside click / Escape.
  useEffect(() => {
    if (!open) return;
    const onDown = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && setOpen(false);
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const name = me.display_name || me.username || me.email || me.user_id;
  const capped = !!usage && usage.percent_used != null && usage.cap_usd != null;
  const status: UsageStatus = usage?.status ?? 'ok';
  const pct = capped ? Math.min(100, Math.max(0, usage!.percent_used!)) : 0;

  return (
    <div ref={ref} className="relative shrink-0">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        title={name}
        className="flex items-center gap-2 rounded-lg border brd bg-[var(--surface-inset)] px-2 py-1.5 transition hover:bg-[var(--surface-2)]"
      >
        <span
          className={`flex h-6 w-6 items-center justify-center rounded-md ${
            me.is_admin ? 'bg-[var(--accent-soft)] t-accent' : 'surf t-dim'
          }`}
        >
          {me.is_admin ? <Shield className="h-3.5 w-3.5" /> : <User className="h-3.5 w-3.5" />}
        </span>
        <span className="hidden text-left leading-tight lg:block">
          <span className="block text-[12px] font-semibold t-primary">{name}</span>
          <span className="block text-[10px] font-medium t-faint">
            {me.is_admin ? t('access.admin') : t('access.read_only')}
          </span>
        </span>
        <ChevronDown
          className={`h-3.5 w-3.5 t-faint transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {open && (
        <div
          role="menu"
          className="glass absolute right-0 z-20 mt-2 w-72 origin-top-right overflow-hidden p-0 shadow-xl"
        >
          {/* Identity */}
          <div className="flex items-center gap-2.5 border-b brd p-3">
            <span
              className={`flex h-9 w-9 items-center justify-center rounded-lg ${
                me.is_admin ? 'bg-[var(--accent-soft)] t-accent' : 'surf t-dim'
              }`}
            >
              {me.is_admin ? <Shield className="h-4 w-4" /> : <User className="h-4 w-4" />}
            </span>
            <div className="min-w-0">
              <div className="truncate text-[13px] font-semibold t-primary">{name}</div>
              {me.email && <div className="truncate text-[11px] t-faint">{me.email}</div>}
            </div>
          </div>

          {/* Monthly LLM consumption */}
          <div className="p-3">
            <div className="mb-2 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide t-faint">
              <Gauge className="h-3.5 w-3.5" />
              {t('usage.title')}
            </div>
            {loading ? (
              <div className="h-9 animate-pulse rounded-md bg-[var(--surface-inset)]" />
            ) : !usage ? (
              <p className="text-[12px] t-dim">{t('usage.untracked')}</p>
            ) : capped ? (
              <>
                <div className="mb-1.5 flex items-baseline justify-between gap-2">
                  <span className="font-display text-2xl font-bold tabular-nums t-primary">
                    {usage.percent_used}%
                  </span>
                  <span className="text-[11px] font-medium tabular-nums t-dim">
                    {usd(usage.spend_usd)} / {usd(usage.cap_usd!)}
                  </span>
                </div>
                <div
                  className="h-2 overflow-hidden rounded-full bg-[var(--surface-inset)]"
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
                <div className="mt-1.5 flex items-center justify-between text-[10.5px]">
                  <span className={STATUS_TEXT[status]}>{t(`usage.status_${status}`)}</span>
                  <span className="t-faint">{formatPeriod(usage.period, i18n.language)}</span>
                </div>
              </>
            ) : (
              <div className="flex items-baseline justify-between gap-2">
                <span className="font-display text-xl font-bold tabular-nums t-primary">
                  {usd(usage.spend_usd)}
                </span>
                <span className="text-[11px] font-medium t-dim">{t('usage.unlimited')}</span>
              </div>
            )}
          </div>

          {/* Logout */}
          <button
            type="button"
            onClick={() => logout()}
            className="flex w-full items-center gap-2 border-t brd px-3 py-2.5 text-[12px] font-medium t-dim transition hover:bg-[var(--surface-2)] hover:text-rose-500"
          >
            <LogOut className="h-4 w-4" />
            {t('access.logout')}
          </button>
        </div>
      )}
    </div>
  );
}
