import { useCallback, useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Database, HardDrive, ListChecks, RefreshCw, Trash2, AlertTriangle } from 'lucide-react';
import { clearCache, fetchCacheStats, fetchDbStatus, fetchQueueStatus, resetDb } from '@/lib/api';
import type { CacheStats, DbStatus, QueueStatus } from '@/types';
import { useControlStore } from '@/store/useControlStore';
import { useUiStore } from '@/store/useUiStore';
import { ErrorNote, KeyValueRow, SectionCard, StatTile, dotClass } from './parts';

interface Data {
  db: DbStatus | null;
  cache: CacheStats | null;
  queue: QueueStatus | null;
}

export function InfraPanel() {
  const { t } = useTranslation();
  const isAdmin = useControlStore((s) => s.me?.is_admin ?? false);
  const ask = useUiStore((s) => s.ask);
  const pushToast = useUiStore((s) => s.pushToast);
  const [data, setData] = useState<Data>({ db: null, cache: null, queue: null });
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [db, cache, queue] = await Promise.all([
        fetchDbStatus(),
        fetchCacheStats(),
        fetchQueueStatus(),
      ]);
      setData({ db, cache, queue });
    } catch (err) {
      setError(err instanceof Error ? err.message : 'failed');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const guarded = useCallback(
    async (confirmKey: string, run: () => Promise<{ ok: boolean; message: string }>) => {
      if (!(await ask(t(confirmKey)))) return;
      setBusy(true);
      try {
        const res = await run();
        pushToast(res.message || (res.ok ? 'OK' : 'failed'), res.ok ? 'success' : 'danger');
        await load();
      } catch (err) {
        pushToast(err instanceof Error ? err.message : 'failed', 'danger');
      } finally {
        setBusy(false);
      }
    },
    [ask, pushToast, t, load]
  );

  const { db, cache, queue } = data;

  return (
    <div className="space-y-5">
      <div className="flex justify-end">
        <button
          type="button"
          onClick={() => void load()}
          disabled={loading}
          className="inline-flex items-center gap-2 rounded-lg border brd bg-[var(--surface-inset)] px-3.5 py-2 text-[13px] font-medium t-dim transition hover:bg-[var(--surface-2)] disabled:opacity-50"
        >
          <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
          {t('console.refresh')}
        </button>
      </div>

      {error && <ErrorNote message={error} />}

      <SectionCard
        icon={Database}
        title={t('console.db')}
        hint={t('console.db_hint')}
        right={
          isAdmin && (
            <button
              type="button"
              disabled={busy}
              onClick={() => void guarded('console.confirm_reset', resetDb)}
              className="inline-flex items-center gap-1.5 rounded-lg border border-rose-500/30 bg-rose-500/5 px-3 py-1.5 text-[12px] font-semibold text-rose-500 transition hover:bg-rose-500/10 disabled:opacity-50"
            >
              <AlertTriangle className="h-3.5 w-3.5" />
              {t('console.reset_db')}
            </button>
          )
        }
      >
        <div className="grid gap-2 sm:grid-cols-2">
          {db?.stores.map((s) => (
            <div
              key={s.database}
              className="flex items-center justify-between gap-3 rounded-lg border brd surf px-3 py-2"
            >
              <div className="min-w-0">
                <div className="text-[13px] font-semibold t-primary">{s.database}</div>
                <div className="truncate text-[11px] t-dim" title={s.details || s.message}>
                  {s.message}
                </div>
              </div>
              <span className={`led shrink-0 ${dotClass(s.online)}`} />
            </div>
          ))}
        </div>
      </SectionCard>

      <div className="grid gap-5 lg:grid-cols-2">
        <SectionCard
          icon={HardDrive}
          title={t('console.cache')}
          hint={t('console.cache_hint')}
          right={
            isAdmin && (
              <button
                type="button"
                disabled={busy}
                onClick={() => void guarded('console.confirm_clear', clearCache)}
                className="inline-flex items-center gap-1.5 rounded-lg border border-rose-500/30 bg-rose-500/5 px-3 py-1.5 text-[12px] font-semibold text-rose-500 transition hover:bg-rose-500/10 disabled:opacity-50"
              >
                <Trash2 className="h-3.5 w-3.5" />
                {t('console.clear_cache')}
              </button>
            )
          }
        >
          {cache?.ok ? (
            <div className="grid grid-cols-2 gap-2">
              <StatTile label={t('console.keys')} value={cache.total_keys ?? '—'} />
              <StatTile label={t('console.used_mem')} value={cache.used_memory_human ?? '—'} />
              <StatTile label={t('console.peak_mem')} value={cache.peak_memory_human ?? '—'} />
              <StatTile label={t('console.frag')} value={cache.fragmentation_ratio ?? '—'} />
            </div>
          ) : (
            <p className="text-[12px] t-dim">{cache?.error ?? t('console.unavailable')}</p>
          )}
        </SectionCard>

        <SectionCard icon={ListChecks} title={t('console.queue')} hint={t('console.queue_hint')}>
          {queue?.available ? (
            <>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                <StatTile label={t('console.workers')} value={queue.workers} />
                <StatTile label={t('console.pending')} value={queue.pending} />
                <StatTile label={t('console.running')} value={queue.running} />
                <StatTile label={t('console.completed')} value={queue.completed} tone="good" />
                <StatTile
                  label={t('console.failed')}
                  value={queue.failed}
                  tone={queue.failed > 0 ? 'bad' : 'neutral'}
                />
              </div>
              {queue.worker_details.length > 0 && (
                <div className="space-y-0.5">
                  {queue.worker_details.map((w) => (
                    <KeyValueRow key={w.name} label={w.name} value={w.state} />
                  ))}
                </div>
              )}
            </>
          ) : (
            <p className="text-[12px] t-dim">{queue?.error ?? t('console.unavailable')}</p>
          )}
        </SectionCard>
      </div>
    </div>
  );
}
