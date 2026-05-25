'use client';

import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useTranslations } from 'next-intl';
import {
  ChevronLeft,
  ChevronRight,
  FileJson,
  FileSpreadsheet,
  RefreshCw,
  ScrollText,
  ShieldCheck,
  ShieldOff,
  X,
} from 'lucide-react';
import { TopBar } from '@/components/TopBar';
import { PageHeader } from '@/components/PageHeader';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { EmptyState } from '@/components/ui/empty-state';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip';
import { ChainBanner } from '@/components/audit/ChainBanner';
import { AuditFiltersBar, type FiltersState } from '@/components/audit/AuditFiltersBar';
import { AuditDetailDrawer } from '@/components/audit/AuditDetailDrawer';
import {
  type AuditEntry,
  type AuditFilters,
  exportAuditCsv,
  exportAuditJson,
  listAuditActions,
  listAuditPage,
  listAuditUsers,
  verifyAuditChain,
} from '@/lib/api/audit';
import { cn } from '@/lib/cn';

const PAGE_SIZE = 100;

export default function AuditPage() {
  const t = useTranslations('audit');
  const qc = useQueryClient();
  const [filters, setFilters] = useState<FiltersState>({
    limit: PAGE_SIZE,
    offset: 0,
  });
  const [resourceInput, setResourceInput] = useState('');
  const [detailSeq, setDetailSeq] = useState<number | null>(null);
  const [exportError, setExportError] = useState<string | null>(null);
  const [verifyToast, setVerifyToast] = useState<{
    msg: string;
    danger: boolean;
  } | null>(null);

  const log = useQuery({
    queryKey: ['audit-log', filters],
    queryFn: () => listAuditPage(filters),
    placeholderData: (prev) => prev,
  });
  const chain = useQuery({
    queryKey: ['audit-chain'],
    queryFn: verifyAuditChain,
  });
  const actions = useQuery({
    queryKey: ['audit-actions'],
    queryFn: listAuditActions,
  });
  const users = useQuery({
    queryKey: ['audit-users'],
    queryFn: listAuditUsers,
  });

  const verifyMut = useMutation({
    mutationFn: verifyAuditChain,
    onSuccess: (s) => {
      qc.setQueryData(['audit-chain'], s);
      setVerifyToast({
        msg: s.ok
          ? t('verified', { count: s.total_entries })
          : t('broken', { seq: s.broken_seq ?? '?' }),
        danger: !s.ok,
      });
      setTimeout(() => setVerifyToast(null), 4000);
    },
    onError: (e) =>
      setVerifyToast({
        msg: t('verifyFailed', { error: (e as Error).message }),
        danger: true,
      }),
  });

  const exportMut = useMutation({
    mutationFn: async (kind: 'csv' | 'json') => {
      const f: AuditFilters = {
        user_id: filters.user_id,
        action: filters.action,
        resource: filters.resource,
        date_from: filters.date_from,
        date_to: filters.date_to,
      };
      if (kind === 'csv') await exportAuditCsv(f);
      else await exportAuditJson(f);
    },
    onError: (e) => setExportError((e as Error).message),
  });

  const total = log.data?.total ?? 0;
  const rows = log.data?.rows ?? [];
  const pageStart = filters.offset + 1;
  const pageEnd = Math.min(filters.offset + rows.length, total);
  const canPrev = filters.offset > 0;
  const canNext = filters.offset + rows.length < total;

  const setFilter = (patch: Partial<FiltersState>) =>
    setFilters((f) => ({ ...f, ...patch, offset: 0 }));

  const clearFilters = () => {
    setResourceInput('');
    setFilters({ limit: PAGE_SIZE, offset: 0 });
  };

  const hasActiveFilters = useMemo(
    () =>
      Boolean(
        filters.user_id ||
        filters.action ||
        filters.resource ||
        filters.date_from ||
        filters.date_to
      ),
    [filters]
  );

  const onSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setFilter({ resource: resourceInput.trim() || undefined });
  };

  return (
    <TooltipProvider>
      <div className="h-screen flex flex-col">
        <TopBar />
        <main className="flex-1 overflow-auto p-6">
          <div className="mx-auto max-w-7xl">
            <PageHeader
              eyebrow={t('eyebrow')}
              eyebrowIcon={ScrollText}
              title={t('title')}
              description={t('description')}
              actions={
                <>
                  <Button
                    variant="secondary"
                    size="md"
                    onClick={() => {
                      log.refetch();
                      chain.refetch();
                    }}
                    disabled={log.isFetching}
                  >
                    <RefreshCw size={13} className={cn(log.isFetching && 'animate-spin')} />{' '}
                    {t('refresh')}
                  </Button>
                  <Button
                    variant="primary"
                    size="md"
                    onClick={() => verifyMut.mutate()}
                    disabled={verifyMut.isPending}
                  >
                    <ShieldCheck size={13} className={cn(verifyMut.isPending && 'animate-pulse')} />
                    {verifyMut.isPending ? t('verifying') : t('verifyChain')}
                  </Button>
                </>
              }
            />

            <ChainBanner status={chain.data} loading={chain.isLoading} />

            <AuditFiltersBar
              actions={actions.data ?? []}
              users={users.data ?? []}
              filters={filters}
              resourceInput={resourceInput}
              setResourceInput={setResourceInput}
              onSearchSubmit={onSearchSubmit}
              setFilter={setFilter}
              clear={clearFilters}
              hasActive={hasActiveFilters}
            />

            <Card className="overflow-hidden">
              <div className="flex items-center justify-between border-b border-border bg-bg-panel-soft px-4 py-3 gap-4 flex-wrap">
                <h2 className="text-sm font-semibold">{t('eventStream')}</h2>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => exportMut.mutate('csv')}
                    disabled={exportMut.isPending}
                  >
                    <FileSpreadsheet size={13} /> {t('csv')}
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => exportMut.mutate('json')}
                    disabled={exportMut.isPending}
                  >
                    <FileJson size={13} /> {t('jsonSigned')}
                  </Button>
                  <span className="text-xs text-text-muted ml-2">
                    {total > 0
                      ? t('rangeOf', {
                          start: pageStart,
                          end: pageEnd,
                          total,
                        })
                      : t('zeroEntries')}
                  </span>
                </div>
              </div>

              {exportError && (
                <div className="border-b border-status-danger/30 bg-status-danger/10 px-4 py-2 text-xs text-status-danger flex items-center justify-between">
                  <span>{t('exportError', { error: exportError })}</span>
                  <button
                    onClick={() => setExportError(null)}
                    className="opacity-70 hover:opacity-100"
                  >
                    <X size={12} />
                  </button>
                </div>
              )}

              {log.isLoading ? (
                <div className="p-4 space-y-2">
                  {Array.from({ length: 8 }).map((_, i) => (
                    <Skeleton key={i} className="h-10" />
                  ))}
                </div>
              ) : rows.length === 0 ? (
                <EmptyState
                  icon={ScrollText}
                  title={t('noEntries')}
                  description={hasActiveFilters ? t('noMatches') : t('noEvents')}
                  action={
                    hasActiveFilters ? (
                      <Button size="sm" variant="ghost" onClick={clearFilters}>
                        {t('clearFilters')}
                      </Button>
                    ) : undefined
                  }
                  className="py-16"
                />
              ) : (
                <div className="overflow-auto">
                  <table className="w-full min-w-[920px] text-xs">
                    <thead className="bg-bg-panel-elev/60 text-text-muted sticky top-0">
                      <tr>
                        <Th>{t('cols.seq')}</Th>
                        <Th>{t('cols.timestamp')}</Th>
                        <Th>{t('cols.user')}</Th>
                        <Th>{t('cols.action')}</Th>
                        <Th>{t('cols.resource')}</Th>
                        <Th>{t('cols.hash')}</Th>
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map((e) => (
                        <Row
                          key={e.seq}
                          entry={e}
                          broken={chain.data?.broken_seq === e.seq}
                          brokenLabel={t('chainBrokenHere')}
                          onClick={() => setDetailSeq(e.seq)}
                        />
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              <div className="flex items-center justify-between border-t border-border px-4 py-2.5 text-xs">
                <span className="text-text-muted">{t('pageSize', { size: PAGE_SIZE })}</span>
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={!canPrev || log.isFetching}
                    onClick={() =>
                      setFilters((f) => ({
                        ...f,
                        offset: Math.max(0, f.offset - PAGE_SIZE),
                      }))
                    }
                  >
                    <ChevronLeft size={13} /> {t('prev')}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={!canNext || log.isFetching}
                    onClick={() =>
                      setFilters((f) => ({
                        ...f,
                        offset: f.offset + PAGE_SIZE,
                      }))
                    }
                  >
                    {t('next')} <ChevronRight size={13} />
                  </Button>
                </div>
              </div>
            </Card>
          </div>

          {verifyToast && (
            <div
              className={cn(
                'fixed bottom-6 right-6 z-50 max-w-sm rounded-lg border px-4 py-3 text-sm shadow-panel animate-fade-in',
                verifyToast.danger
                  ? 'bg-status-danger/15 border-status-danger/40 text-status-danger'
                  : 'bg-status-success/15 border-status-success/40 text-status-success'
              )}
            >
              {verifyToast.msg}
            </div>
          )}

          {detailSeq !== null && (
            <AuditDetailDrawer seq={detailSeq} onClose={() => setDetailSeq(null)} />
          )}
        </main>
      </div>
    </TooltipProvider>
  );
}

function Row({
  entry,
  broken,
  brokenLabel,
  onClick,
}: {
  entry: AuditEntry;
  broken: boolean;
  brokenLabel: string;
  onClick: () => void;
}) {
  return (
    <tr
      onClick={onClick}
      className={cn(
        'border-t border-border cursor-pointer transition-colors',
        broken ? 'bg-status-danger/15 hover:bg-status-danger/25' : 'hover:bg-bg-panel-elev'
      )}
    >
      <Td className="font-mono text-text-secondary tabular-nums">
        <div className="flex items-center gap-1.5">
          {broken && (
            <Tooltip>
              <TooltipTrigger asChild>
                <ShieldOff size={12} className="text-status-danger" />
              </TooltipTrigger>
              <TooltipContent>{brokenLabel}</TooltipContent>
            </Tooltip>
          )}
          {entry.seq}
        </div>
      </Td>
      <Td className="text-text-muted whitespace-nowrap">{new Date(entry.ts).toLocaleString()}</Td>
      <Td className="font-mono text-text-secondary">{entry.user_email ?? entry.user_id ?? '—'}</Td>
      <Td>
        <span className="inline-flex items-center rounded-md border border-border bg-bg-canvas px-2 py-1 font-mono text-[11px]">
          {entry.action}
        </span>
      </Td>
      <Td className="max-w-[280px] truncate font-mono text-text-muted">{entry.resource ?? '—'}</Td>
      <Td className="font-mono text-text-muted">{entry.entry_hash.slice(0, 24)}…</Td>
    </tr>
  );
}

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="px-3 py-3 text-left text-[10px] font-semibold uppercase tracking-wide">
      {children}
    </th>
  );
}
function Td({ children, className }: { children: React.ReactNode; className?: string }) {
  return <td className={cn('px-3 py-3', className)}>{children}</td>;
}
