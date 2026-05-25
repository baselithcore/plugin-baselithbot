'use client';

import { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import {
  Brain,
  ChevronDown,
  ChevronRight,
  Loader2,
  RefreshCw,
  ShieldAlert,
  Sparkles,
  type LucideIcon,
} from 'lucide-react';
import { useTranslations } from 'next-intl';
import { getReportSummary, type ReportSummary } from '@/lib/api';
import { cn } from '@/lib/cn';
import { useLocaleStore } from '@/lib/i18n/store';

interface Props {
  reportId: string;
  findingsCount: number;
}

const VERDICT_TONE: Record<ReportSummary['verdict'], { pill: string; icon: string }> = {
  compliant: {
    pill: 'border-status-success/30 bg-status-success/10 text-status-success',
    icon: 'text-status-success',
  },
  attention: {
    pill: 'border-status-warning/30 bg-status-warning/10 text-status-warning',
    icon: 'text-status-warning',
  },
  critical: {
    pill: 'border-status-danger/30 bg-status-danger/10 text-status-danger',
    icon: 'text-status-danger',
  },
};

export function WorkspaceVerdict({ reportId, findingsCount }: Props) {
  const t = useTranslations('scan.verdict');
  const locale = useLocaleStore((s) => s.locale);
  const [open, setOpen] = useState(true);

  const query = useQuery<ReportSummary>({
    queryKey: ['summary', reportId, locale],
    queryFn: () => getReportSummary(reportId, locale),
    staleTime: 10 * 60 * 1000,
    retry: 1,
  });

  const regen = useMutation({
    mutationFn: () => getReportSummary(reportId, locale),
    onSuccess: (data) => {
      query.refetch();
      // Optimistically swap by writing through TanStack cache.
      // refetch already updates; explicit set avoided to keep code small.
      void data;
    },
  });

  const summary = query.data;
  const loading = query.isLoading || regen.isPending;
  const errorMsg =
    (query.error instanceof Error && query.error.message) ||
    (regen.error instanceof Error && regen.error.message) ||
    null;

  const tone = summary ? VERDICT_TONE[summary.verdict] : null;

  return (
    <div className="rounded-xl border border-border surface-elev shadow-inner-soft overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="w-full px-4 py-2.5 flex items-center justify-between gap-3 hover:bg-bg-panel-elev/40 transition-colors ring-focus"
      >
        <div className="flex items-center gap-2 min-w-0">
          <Sparkles size={13} className="text-status-info shrink-0" />
          <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-text-muted">
            {t('scanVerdict')}
          </span>
          {summary && tone && (
            <span
              className={cn(
                'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider ml-1',
                tone.pill
              )}
            >
              <Brain size={10} />
              {summary.verdict}
            </span>
          )}
          {summary?.fallback && (
            <span
              className="inline-flex items-center rounded-full border border-status-warning/30 bg-status-warning/10 px-1.5 py-0.5 text-[9px] font-mono uppercase text-status-warning"
              title={t('fallbackHint')}
            >
              {t('fallback')}
            </span>
          )}
          {loading && !summary && <Loader2 size={11} className="animate-spin text-text-muted" />}
        </div>
        <ChevronDown
          size={14}
          className={cn(
            'text-text-muted transition-transform duration-200 shrink-0',
            open && 'rotate-180'
          )}
        />
      </button>

      {open && (
        <div className="border-t border-border px-4 py-3 space-y-3 animate-slide-up">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <h3 className="text-[13px] font-semibold leading-snug tracking-tight text-text-primary">
                {loading
                  ? t('judging')
                  : summary?.headline ||
                    (errorMsg ? t('headlineUnavailable') : t('headlineAwaiting'))}
              </h3>
              <p className="mt-1.5 text-[12px] leading-5 text-text-secondary">
                {loading ? (
                  <span className="inline-flex items-center gap-1.5 text-text-muted text-[11px]">
                    <Loader2 size={11} className="animate-spin" />
                    {t('synthesizing', { count: findingsCount })}
                  </span>
                ) : summary?.assessment ? (
                  summary.assessment
                ) : errorMsg ? (
                  <span className="text-status-warning text-[11px]">{errorMsg}</span>
                ) : null}
              </p>
            </div>
            <button
              type="button"
              onClick={() => regen.mutate()}
              disabled={loading}
              title={loading ? t('generating') : t('regenerate')}
              className="inline-flex h-7 items-center gap-1.5 rounded-md border border-border bg-bg-canvas px-2 text-[10.5px] text-text-muted hover:text-text-primary hover:bg-bg-panel-elev transition-colors ring-focus disabled:opacity-50 shrink-0"
            >
              <RefreshCw size={11} className={loading ? 'animate-spin' : ''} />
              {loading ? t('generating') : t('regenerate')}
            </button>
          </div>

          {summary && (summary.top_risks.length > 0 || summary.next_steps.length > 0) && (
            <div className="grid gap-2.5 md:grid-cols-2">
              {summary.top_risks.length > 0 && (
                <BulletBox
                  icon={ShieldAlert}
                  title={t('topRisks')}
                  tone="danger"
                  items={summary.top_risks}
                />
              )}
              {summary.next_steps.length > 0 && (
                <BulletBox
                  icon={ChevronRight}
                  title={t('nextSteps')}
                  tone="info"
                  items={summary.next_steps}
                />
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function BulletBox({
  icon: Icon,
  title,
  tone,
  items,
}: {
  icon: LucideIcon;
  title: string;
  tone: 'danger' | 'info';
  items: string[];
}) {
  const cls =
    tone === 'danger'
      ? 'border-status-danger/25 bg-status-danger/5'
      : 'border-status-info/25 bg-status-info/5';
  const iconCls = tone === 'danger' ? 'text-status-danger' : 'text-status-info';
  const dotCls = tone === 'danger' ? 'bg-status-danger' : 'bg-status-info';
  return (
    <div className={cn('rounded-lg border p-2.5', cls)}>
      <div className="flex items-center gap-1.5 text-[10px] uppercase tracking-wider text-text-secondary font-semibold">
        <Icon size={11} className={iconCls} />
        {title}
      </div>
      <ul className="mt-1.5 space-y-1">
        {items.map((it, i) => (
          <li
            key={i}
            className="flex items-start gap-2 text-[11.5px] text-text-secondary leading-5"
          >
            <span className={cn('mt-1.5 h-1 w-1 rounded-full shrink-0', dotCls)} />
            <span>{it}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
