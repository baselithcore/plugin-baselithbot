import { useEffect, useState } from 'react';
import { motion } from 'motion/react';
import { useTranslation } from 'react-i18next';
import {
  Shield,
  User,
  LogOut,
  Gauge,
  ArrowLeft,
  AtSign,
  Fingerprint,
  KeyRound,
} from 'lucide-react';
import { fetchMyLlmUsage, logout } from '@/lib/api';
import { useControlStore } from '@/store/useControlStore';
import { pageVariants } from '@/lib/motion';
import { UsageGauge } from '@/components/widgets/UsageGauge';
import type { Me, MyLlmUsage } from '@/types';

// A single labelled identity row: icon + caption + selectable value.
function InfoRow({
  icon: Icon,
  label,
  value,
  mono,
}: {
  icon: typeof AtSign;
  label: string;
  value: string;
  mono?: boolean;
}) {
  return (
    <div className="flex items-center gap-3 px-4 py-3">
      <Icon className="h-4 w-4 shrink-0 t-faint" />
      <span className="w-28 shrink-0 text-[11px] font-medium uppercase tracking-wide t-faint">
        {label}
      </span>
      <span
        className={`min-w-0 flex-1 select-all truncate text-[13px] t-primary ${mono ? 'font-mono text-[12px]' : ''}`}
        title={value}
      >
        {value}
      </span>
    </div>
  );
}

// Compact self-service account page: identity, roles/access, and month-to-date
// LLM spend (vs the effective cap served by the auth plugin), plus logout.
export function Account({ me }: { me: Me }) {
  const { t } = useTranslation();
  const setTab = useControlStore((s) => s.setTab);
  const [usage, setUsage] = useState<MyLlmUsage | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    fetchMyLlmUsage()
      .then((u) => alive && setUsage(u))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, []);

  const name = me.display_name || me.username || me.email || me.user_id;

  return (
    <motion.div
      variants={pageVariants}
      initial="hidden"
      animate="show"
      exit="exit"
      className="mx-auto max-w-2xl space-y-4"
    >
      <button
        type="button"
        onClick={() => setTab('dashboard')}
        className="inline-flex items-center gap-1.5 text-[13px] font-medium t-dim transition hover:text-[var(--text)]"
      >
        <ArrowLeft className="h-4 w-4" />
        {t('detail.back')}
      </button>

      {/* Identity header */}
      <div className="glass flex items-center gap-4 p-5">
        <span
          className={`flex h-14 w-14 shrink-0 items-center justify-center rounded-xl ${
            me.is_admin ? 'bg-[var(--accent-soft)] t-accent' : 'surf t-dim'
          }`}
        >
          {me.is_admin ? <Shield className="h-6 w-6" /> : <User className="h-6 w-6" />}
        </span>
        <div className="min-w-0">
          <h1 className="truncate font-display text-xl font-bold tracking-tight t-primary">
            {name}
          </h1>
          {me.email && <p className="truncate text-[13px] t-dim">{me.email}</p>}
          <span
            className={`mt-1.5 inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-[11px] font-semibold ${
              me.is_admin
                ? 'border-[var(--accent-border)] bg-[var(--accent-soft)] t-accent'
                : 'brd t-dim'
            }`}
          >
            {me.is_admin ? <Shield className="h-3 w-3" /> : <User className="h-3 w-3" />}
            {me.is_admin ? t('access.admin') : t('access.read_only')}
          </span>
        </div>
      </div>

      {/* Identity details */}
      <div className="glass overflow-hidden">
        <div className="divide-y divide-[var(--border)]">
          <InfoRow icon={AtSign} label={t('account.username')} value={me.username || '—'} />
          <InfoRow icon={KeyRound} label={t('account.email')} value={me.email || '—'} />
          {me.tenant_id && (
            <InfoRow icon={Fingerprint} label={t('account.tenant')} value={me.tenant_id} mono />
          )}
          <InfoRow icon={Fingerprint} label={t('account.user_id')} value={me.user_id} mono />
        </div>
        {me.roles.length > 0 && (
          <div className="flex flex-wrap items-center gap-2 border-t brd px-4 py-3">
            <span className="text-[11px] font-medium uppercase tracking-wide t-faint">
              {t('account.roles')}
            </span>
            {me.roles.map((r) => (
              <span
                key={r}
                className="rounded-md border brd bg-[var(--surface-inset)] px-2 py-0.5 font-mono text-[11px] t-dim"
              >
                {r}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Monthly LLM consumption */}
      <div className="glass p-5">
        <div className="mb-3 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide t-faint">
          <Gauge className="h-3.5 w-3.5" />
          {t('usage.title')}
        </div>
        <UsageGauge usage={usage} loading={loading} size="md" moneyless />
      </div>

      {/* Logout */}
      <button
        type="button"
        onClick={() => logout()}
        className="glass glass-interactive flex w-full items-center justify-center gap-2 p-3 text-[13px] font-semibold t-dim transition hover:text-rose-500"
      >
        <LogOut className="h-4 w-4" />
        {t('access.logout')}
      </button>
    </motion.div>
  );
}
