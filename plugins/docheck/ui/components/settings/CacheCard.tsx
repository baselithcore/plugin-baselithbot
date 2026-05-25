'use client';

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Activity, Loader2, RotateCcw } from 'lucide-react';
import { toast } from 'sonner';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/button';
import { getCacheState, resetCacheMetrics } from '@/lib/api/system';
import { Mono, Row, Section, StatusPill } from './SettingsShared';

const TARGET_RATIO = 0.6;

export function CacheCard({ isAdmin }: { isAdmin: boolean }) {
  const t = useTranslations('settings.cache');
  const qc = useQueryClient();
  const cache = useQuery({
    queryKey: ['system', 'cache'],
    queryFn: getCacheState,
    refetchInterval: 10_000,
  });

  const resetMut = useMutation({
    mutationFn: resetCacheMetrics,
    onSuccess: () => {
      toast.success(t('toastReset'));
      qc.invalidateQueries({ queryKey: ['system', 'cache'] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const c = cache.data;
  const ratio = c?.metrics.hit_ratio ?? 0;
  const ratioPct = Math.round(ratio * 100);
  const tone = ratio >= TARGET_RATIO ? 'success' : c && c.metrics.total > 0 ? 'warning' : 'muted';

  return (
    <Section
      title={t('title')}
      icon={Activity}
      actions={
        isAdmin && (
          <Button
            size="sm"
            variant="ghost"
            onClick={() => resetMut.mutate()}
            disabled={resetMut.isPending}
          >
            {resetMut.isPending ? (
              <Loader2 size={13} className="animate-spin" />
            ) : (
              <RotateCcw size={13} />
            )}
            {t('resetMetrics')}
          </Button>
        )
      }
    >
      <Row label={t('hitRatio')}>
        <span className="inline-flex flex-col items-end gap-1.5 min-w-0 w-full">
          <span className="inline-flex items-center gap-2">
            <StatusPill tone={tone}>{ratioPct}%</StatusPill>
            <span className="text-[11px] text-text-muted">
              {t('target', { pct: TARGET_RATIO * 100 })}
            </span>
          </span>
          <span className="block w-full max-w-[220px] h-1.5 rounded-full bg-bg-canvas border border-border overflow-hidden">
            <span
              className={`block h-full ${
                tone === 'success'
                  ? 'bg-status-success'
                  : tone === 'warning'
                    ? 'bg-status-warning'
                    : 'bg-text-muted'
              } transition-all duration-500`}
              style={{ width: `${Math.min(100, ratioPct)}%` }}
            />
          </span>
        </span>
      </Row>
      <Row label={t('hitsMisses')}>
        <Mono>{c ? `${c.metrics.hits} / ${c.metrics.misses}` : '…'}</Mono>
      </Row>
      <Row label={t('verdictRows')}>
        <Mono>{c ? c.verdict_rows : '…'}</Mono>
      </Row>
      <Row label={t('embeddingRows')}>
        <Mono>{c ? c.embedding_rows : '…'}</Mono>
      </Row>
    </Section>
  );
}
