'use client';

import { ShieldAlert, ShieldCheck } from 'lucide-react';
import { useFormatter, useTranslations } from 'next-intl';
import { Skeleton } from '@/components/ui/skeleton';
import type { ChainStatus } from '@/lib/api/audit';
import { cn } from '@/lib/cn';

export function ChainBanner({ status, loading }: { status?: ChainStatus; loading: boolean }) {
  const t = useTranslations('audit.banner');
  const fmt = useFormatter();
  if (loading) return <Skeleton className="mb-5 h-20" />;
  if (!status) return null;
  return (
    <div
      className={cn(
        'mb-5 rounded-xl border p-4 shadow-panel animate-fade-in',
        status.ok
          ? 'bg-status-success/10 border-status-success/30 text-status-success'
          : 'bg-status-danger/10 border-status-danger/30 text-status-danger'
      )}
    >
      <div className="flex items-center gap-3">
        <div
          className={cn(
            'flex h-10 w-10 items-center justify-center rounded-lg border',
            status.ok
              ? 'border-status-success/30 bg-status-success/15'
              : 'border-status-danger/30 bg-status-danger/15'
          )}
        >
          {status.ok ? <ShieldCheck size={20} /> : <ShieldAlert size={20} />}
        </div>
        <div className="flex-1">
          <div className="text-sm font-semibold">
            {status.ok ? t('verified') : t('broken', { seq: status.broken_seq ?? '?' })}
          </div>
          <div className="mt-0.5 text-xs opacity-80">
            {t('stats', {
              count: status.total_entries,
              when: fmt.dateTime(new Date(status.verified_at), {
                dateStyle: 'medium',
                timeStyle: 'short',
              }),
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
