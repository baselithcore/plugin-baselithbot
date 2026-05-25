/**
 * AdminFeedbackPage — monitoraggio + triage + moderazione feedback.
 *
 * Layout enterprise (pattern Helicone / LangSmith / PostHog / Linear):
 *
 * - Top stats bar: anomaly banner + KPI cards + trend + status breakdown
 *   + source-correlation card.
 * - Filter bar: periodo / rating / status / tag / search / user_id + CSV.
 * - Tabella paginata: data, rating, status, tag chips, utente, snippet
 *   domanda, # fonti, motivazione.
 * - Click riga → drawer dettaglio (triage panel + jump-to-conversation
 *   + delete moderazione).
 *
 * URL deep-link: ``/admin/feedback?id=<uuid>`` apre il drawer al load
 * (link condivisibili in Slack / mail moderazione).
 *
 * Gating: ``feedback.read`` per pagina (server + UI guard). Triage e
 * delete gated separatamente nel drawer.
 */

import { ThumbsDown, ThumbsUp } from 'lucide-react';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { toast } from 'sonner';

import { useAuth } from '../../contexts/AuthContext';
import * as feedbackApi from '../../lib/api/feedback_admin';
import type {
  FeedbackFilters,
  FeedbackItem,
  FeedbackSourceStat,
  FeedbackStats,
  FeedbackStatus,
} from '../../lib/api/feedback_admin';
import { Callout } from '../ui';
import { Td, Th } from './users/atoms';
import { RatingPill } from './feedback/atoms';
import { FeedbackDetailDrawer } from './feedback/FeedbackDetailDrawer';
import { FeedbackFiltersBar } from './feedback/FeedbackFiltersBar';
import { FeedbackStatsBar } from './feedback/FeedbackStatsBar';

const PAGE_SIZE = 50;

const STATUS_DOT: Record<FeedbackStatus, string> = {
  open: 'bg-amber-500',
  triaged: 'bg-sky-500',
  resolved: 'bg-emerald-500',
  dismissed: 'bg-zinc-400',
};

function defaultFilters(): FeedbackFilters {
  const d = new Date(Date.now() - 7 * 24 * 3600 * 1000);
  return {
    since: d.toISOString(),
    limit: PAGE_SIZE,
    offset: 0,
  };
}

function readUrlId(): string | null {
  if (typeof window === 'undefined') return null;
  return new URLSearchParams(window.location.search).get('id');
}

function setUrlId(id: string | null): void {
  if (typeof window === 'undefined') return;
  const url = new URL(window.location.href);
  if (id) url.searchParams.set('id', id);
  else url.searchParams.delete('id');
  window.history.replaceState({}, '', url.toString());
}

function fmtDateShort(iso: string | null): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('it-IT', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

function truncate(s: string | null, n: number): string {
  if (!s) return '—';
  const t = s.trim();
  return t.length > n ? t.slice(0, n - 1) + '…' : t;
}

export function AdminFeedbackPage() {
  const { can } = useAuth();
  const allowed = can('feedback.read');
  const [filters, setFilters] = useState<FeedbackFilters>(defaultFilters);
  const [items, setItems] = useState<FeedbackItem[]>([]);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState<FeedbackStats | null>(null);
  const [sourceStats, setSourceStats] = useState<FeedbackSourceStat[]>([]);
  const [suggestedTags, setSuggestedTags] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [statsLoading, setStatsLoading] = useState(false);
  const [sourcesLoading, setSourcesLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(readUrlId);

  // Meta una volta sola al mount (vocabolario tag suggeriti).
  useEffect(() => {
    if (!allowed) return;
    feedbackApi
      .fetchMeta()
      .then((m) => setSuggestedTags(m.suggested_tags))
      .catch(() => setSuggestedTags([]));
  }, [allowed]);

  const refresh = useCallback(async () => {
    if (!allowed) return;
    setLoading(true);
    setError(null);
    try {
      const data = await feedbackApi.listFeedback({
        ...filters,
        limit: PAGE_SIZE,
      });
      setItems(data.items);
      setTotal(data.total);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'errore caricamento');
    } finally {
      setLoading(false);
    }
  }, [filters, allowed]);

  const refreshStats = useCallback(async () => {
    if (!allowed) return;
    setStatsLoading(true);
    setSourcesLoading(true);
    try {
      const [s, src] = await Promise.all([
        feedbackApi.fetchStats({
          since: filters.since,
          until: filters.until,
          bucket: 'day',
        }),
        feedbackApi
          .fetchSourceStats({
            since: filters.since,
            until: filters.until,
            limit: 10,
          })
          .catch(() => []),
      ]);
      setStats(s);
      setSourceStats(src);
    } catch (e) {
      // eslint-disable-next-line no-console
      console.warn('[feedback] stats failed', e);
    } finally {
      setStatsLoading(false);
      setSourcesLoading(false);
    }
  }, [filters.since, filters.until, allowed]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  useEffect(() => {
    void refreshStats();
  }, [refreshStats]);

  // Sync deep-link <-> selectedId.
  useEffect(() => {
    setUrlId(selectedId);
  }, [selectedId]);

  const onFiltersChange = useCallback((next: FeedbackFilters) => {
    setFilters((prev) => ({ ...prev, ...next, offset: 0 }));
  }, []);

  const onPickStatus = useCallback((statusKey: FeedbackStatus) => {
    setFilters((prev) => ({
      ...prev,
      status: prev.status === statusKey ? null : statusKey,
      offset: 0,
    }));
  }, []);

  const onPageChange = useCallback((nextOffset: number) => {
    setFilters((prev) => ({ ...prev, offset: nextOffset }));
  }, []);

  const onDownload = useCallback(async () => {
    try {
      await feedbackApi.downloadCsv(filters);
      toast.success('Export CSV avviato');
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'export fallito');
    }
  }, [filters]);

  const onUpdated = useCallback(
    (updated: FeedbackItem) => {
      setItems((prev) => prev.map((i) => (i.id === updated.id ? updated : i)));
      void refreshStats();
    },
    [refreshStats]
  );

  const onDeleted = useCallback(
    (id: string) => {
      setItems((prev) => prev.filter((i) => i.id !== id));
      setTotal((t) => Math.max(0, t - 1));
      void refreshStats();
    },
    [refreshStats]
  );

  const page = useMemo(() => {
    const offset = filters.offset ?? 0;
    const from = total === 0 ? 0 : offset + 1;
    const to = Math.min(offset + items.length, total);
    return { offset, from, to };
  }, [filters.offset, items.length, total]);

  if (!allowed) {
    return (
      <div className="p-8">
        <Callout tone="warning">
          Permesso ``feedback.read`` richiesto per accedere al monitoraggio feedback.
        </Callout>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col">
      <FeedbackStatsBar
        stats={stats}
        sources={sourceStats}
        loading={statsLoading}
        sourcesLoading={sourcesLoading}
        onPickStatus={onPickStatus}
      />
      <FeedbackFiltersBar
        value={filters}
        total={total}
        loading={loading}
        canDownload={allowed}
        suggestedTags={suggestedTags}
        onChange={onFiltersChange}
        onRefresh={() => {
          void refresh();
          void refreshStats();
        }}
        onDownload={() => void onDownload()}
      />

      {error && (
        <Callout tone="warning" className="m-5">
          {error}
        </Callout>
      )}

      <div className="flex-1 overflow-y-auto">
        <table className="w-full border-separate border-spacing-0 text-xs">
          <thead className="sticky top-0 z-10 bg-[var(--color-canvas)] text-[10px] uppercase text-ink-subtle">
            <tr>
              <Th>Data</Th>
              <Th>Rating</Th>
              <Th>Stato</Th>
              <Th>Tag</Th>
              <Th>Utente</Th>
              <Th>Domanda</Th>
              <Th>Motivazione</Th>
              <Th>Fonti</Th>
            </tr>
          </thead>
          <tbody>
            {loading && items.length === 0 && (
              <tr>
                <td colSpan={8} className="px-5 py-10 text-center text-ink-subtle">
                  Caricamento…
                </td>
              </tr>
            )}
            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={8} className="px-5 py-10 text-center text-ink-subtle">
                  Nessun feedback nel periodo / filtri selezionati.
                </td>
              </tr>
            )}
            {items.map((it) => {
              const isSel = it.id === selectedId;
              return (
                <tr
                  key={it.id}
                  onClick={() => setSelectedId(it.id)}
                  className={
                    'cursor-pointer border-b border-[var(--color-border)] ' +
                    (isSel
                      ? 'bg-[var(--color-brand-soft)]'
                      : 'hover:bg-[var(--color-surface-hover)]')
                  }
                >
                  <Td className="whitespace-nowrap text-ink-subtle">
                    {fmtDateShort(it.created_at)}
                  </Td>
                  <Td>
                    <RatingPill rating={it.rating} />
                  </Td>
                  <Td>
                    <span className="inline-flex items-center gap-1 text-[11px] capitalize">
                      <span
                        className={'size-1.5 rounded-full ' + STATUS_DOT[it.status]}
                        aria-hidden
                      />
                      {it.status}
                    </span>
                  </Td>
                  <Td>
                    {it.tags.length === 0 ? (
                      <span className="text-ink-subtle">—</span>
                    ) : (
                      <span className="flex flex-wrap gap-0.5">
                        {it.tags.slice(0, 3).map((t) => (
                          <span
                            key={t}
                            className="rounded bg-[var(--color-surface)] px-1 py-0.5 text-[10px] text-ink-subtle"
                          >
                            {t}
                          </span>
                        ))}
                        {it.tags.length > 3 && (
                          <span className="text-[10px] text-ink-subtle">
                            +{it.tags.length - 3}
                          </span>
                        )}
                      </span>
                    )}
                  </Td>
                  <Td className="font-mono text-[11px] text-ink-subtle">
                    {it.user_email ??
                      (it.user_id ? it.user_id.slice(0, 8) + '…' : '—')}
                  </Td>
                  <Td>
                    <span className="line-clamp-1 max-w-[360px]">
                      {truncate(it.question, 140)}
                    </span>
                  </Td>
                  <Td>
                    {it.reason ? (
                      <span className="line-clamp-1 max-w-[200px] text-ink-subtle">
                        {truncate(it.reason, 80)}
                      </span>
                    ) : (
                      <span className="text-ink-subtle">—</span>
                    )}
                  </Td>
                  <Td className="text-center text-ink-subtle">
                    {it.sources?.length ?? 0}
                  </Td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <PaginationFooter
        from={page.from}
        to={page.to}
        total={total}
        loading={loading}
        canPrev={page.offset > 0}
        canNext={page.offset + items.length < total}
        onPrev={() => onPageChange(Math.max(0, page.offset - PAGE_SIZE))}
        onNext={() => onPageChange(page.offset + PAGE_SIZE)}
      />

      <FeedbackDetailDrawer
        feedbackId={selectedId}
        suggestedTags={suggestedTags}
        onClose={() => setSelectedId(null)}
        onUpdated={onUpdated}
        onDeleted={onDeleted}
      />
    </div>
  );
}

function PaginationFooter({
  from,
  to,
  total,
  loading,
  canPrev,
  canNext,
  onPrev,
  onNext,
}: {
  from: number;
  to: number;
  total: number;
  loading: boolean;
  canPrev: boolean;
  canNext: boolean;
  onPrev: () => void;
  onNext: () => void;
}) {
  return (
    <footer className="flex items-center justify-between border-t border-[var(--color-border)] px-5 py-2.5 text-[11px]">
      <span className="inline-flex items-center gap-3 text-ink-subtle">
        <span>
          {from}–{to} di {total}
        </span>
        <span className="inline-flex items-center gap-1">
          <ThumbsUp size={11} className="text-emerald-500" /> /
          <ThumbsDown size={11} className="text-rose-500" /> aggregati nel periodo
        </span>
      </span>
      <span className="inline-flex items-center gap-2">
        <button
          type="button"
          disabled={!canPrev || loading}
          onClick={onPrev}
          className="btn-secondary disabled:opacity-40"
        >
          ← Precedenti
        </button>
        <button
          type="button"
          disabled={!canNext || loading}
          onClick={onNext}
          className="btn-secondary disabled:opacity-40"
        >
          Successivi →
        </button>
      </span>
    </footer>
  );
}
