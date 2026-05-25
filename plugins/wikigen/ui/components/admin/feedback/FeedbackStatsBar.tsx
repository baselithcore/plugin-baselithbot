/**
 * FeedbackStatsBar — pannello KPI per la pagina admin feedback.
 *
 * Sezioni:
 * 1. Anomaly banner (se ``stats.anomaly`` populated → spike rilevato).
 * 2. KPI cards 4-col: Totale / Positivi / Negativi / Trend mini-chart.
 * 3. Riga secondary: % positivo bar + top question critica.
 * 4. Status triage breakdown (open/triaged/resolved/dismissed) cliccabili
 *    per filtrare la tabella sotto.
 * 5. Source-correlation: top documenti con down_rate alto (chiude il
 *    loop ingest ↔ moderazione).
 */

import {
  AlertTriangle,
  Inbox,
  MessageSquare,
  ThumbsDown,
  ThumbsUp,
} from 'lucide-react';

import type {
  FeedbackSourceStat,
  FeedbackStats,
  FeedbackStatus,
} from '../../../lib/api/feedback_admin';
import { PercentBar, Sparkline, StatCard } from './atoms';

interface Props {
  stats: FeedbackStats | null;
  sources: FeedbackSourceStat[];
  loading: boolean;
  sourcesLoading: boolean;
  onPickStatus: (status: FeedbackStatus) => void;
}

const STATUS_DEF: Array<{
  key: keyof FeedbackStats['status_breakdown'];
  status: FeedbackStatus;
  label: string;
  tone: string;
}> = [
  {
    key: 'open',
    status: 'open',
    label: 'Aperti',
    tone: 'bg-amber-500/10 text-amber-700 dark:text-amber-400',
  },
  {
    key: 'triaged',
    status: 'triaged',
    label: 'In lavorazione',
    tone: 'bg-sky-500/10 text-sky-700 dark:text-sky-400',
  },
  {
    key: 'resolved',
    status: 'resolved',
    label: 'Risolti',
    tone: 'bg-emerald-500/10 text-emerald-700 dark:text-emerald-400',
  },
  {
    key: 'dismissed',
    status: 'dismissed',
    label: 'Archiviati',
    tone: 'bg-zinc-500/10 text-zinc-600 dark:text-zinc-300',
  },
];

export function FeedbackStatsBar({
  stats,
  sources,
  loading,
  sourcesLoading,
  onPickStatus,
}: Props) {
  if (loading && !stats) {
    return (
      <div className="grid grid-cols-1 gap-3 px-5 py-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <div
            key={i}
            className="h-[88px] animate-pulse rounded-lg bg-[var(--color-surface)] ring-1 ring-[var(--color-border)]"
          />
        ))}
      </div>
    );
  }
  if (!stats) return null;
  const topNegative = stats.top_questions[0];
  const anomaly = stats.anomaly;
  return (
    <section className="border-b border-[var(--color-border)] px-5 py-4">
      {anomaly && (
        <div
          role="alert"
          className={
            'mb-3 flex items-start gap-2 rounded-md p-3 text-xs ring-1 ' +
            (anomaly.severity === 'high'
              ? 'bg-rose-500/10 ring-rose-500/30 text-rose-800 dark:text-rose-200'
              : 'bg-amber-500/10 ring-amber-500/30 text-amber-800 dark:text-amber-200')
          }
        >
          <AlertTriangle size={14} className="mt-0.5 shrink-0" />
          <div className="flex-1">
            <strong className="font-semibold">
              Anomalia rilevata ({anomaly.severity === 'high' ? 'alta' : 'attenzione'})
            </strong>
            <p className="mt-0.5 leading-snug">{anomaly.message}</p>
            <p className="mt-0.5 font-mono text-[10px] opacity-80">
              24h: {(anomaly.down_rate_24h * 100).toFixed(1)}% · baseline 7gg:{' '}
              {(anomaly.down_rate_baseline * 100).toFixed(1)}% · ratio ×{anomaly.ratio}
            </p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Totale"
          value={stats.total}
          hint={`${stats.unique_users} utenti distinti · ${stats.with_reason} con motivazione`}
          icon={<MessageSquare size={14} />}
        />
        <StatCard
          label="Positivi"
          value={stats.up}
          tone="success"
          hint={`${Math.round(stats.positive_rate * 100)}% del totale`}
          icon={<ThumbsUp size={14} />}
        />
        <StatCard
          label="Negativi"
          value={stats.down}
          tone="danger"
          hint={
            stats.total
              ? `${Math.round((stats.down / stats.total) * 100)}% del totale`
              : '—'
          }
          icon={<ThumbsDown size={14} />}
        />
        <div className="flex flex-col gap-2 rounded-lg bg-[var(--color-surface)] p-4 ring-1 ring-[var(--color-border)]">
          <span className="text-[10px] uppercase tracking-wide text-ink-subtle">
            Trend nel periodo
          </span>
          <Sparkline series={stats.trend} />
          <div className="flex items-center gap-3 text-[10px] text-ink-subtle">
            <span className="inline-flex items-center gap-1">
              <span className="size-2 rounded-full bg-emerald-500" />
              up
            </span>
            <span className="inline-flex items-center gap-1">
              <span className="size-2 rounded-full bg-rose-500" />
              down
            </span>
            <span className="ml-auto">{stats.trend.length} bucket</span>
          </div>
        </div>
      </div>

      <div className="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-2">
        <div className="rounded-lg bg-[var(--color-surface)] p-4 ring-1 ring-[var(--color-border)]">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-[10px] uppercase tracking-wide text-ink-subtle">
              Tasso positivo
            </span>
            <span className="text-[10px] text-ink-subtle">
              soglia salute ≥ 70%
            </span>
          </div>
          <PercentBar pct={stats.positive_rate} />
        </div>
        <div className="rounded-lg bg-[var(--color-surface)] p-4 ring-1 ring-[var(--color-border)]">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-[10px] uppercase tracking-wide text-ink-subtle">
              Top domanda critica
            </span>
            {topNegative && topNegative.down > 0 && (
              <span className="inline-flex items-center gap-1 text-[10px] text-rose-600 dark:text-rose-400">
                <AlertTriangle size={11} />
                {topNegative.down} negativi
              </span>
            )}
          </div>
          {topNegative ? (
            <p className="line-clamp-2 text-xs text-ink">
              {topNegative.question}
              <span className="ml-2 text-ink-subtle">
                ({topNegative.count} occorrenze)
              </span>
            </p>
          ) : (
            <p className="text-xs text-ink-subtle">
              Nessuna domanda ricorrente nel periodo.
            </p>
          )}
        </div>
      </div>

      <div className="mt-3 grid grid-cols-1 gap-3 lg:grid-cols-2">
        <div className="rounded-lg bg-[var(--color-surface)] p-3 ring-1 ring-[var(--color-border)]">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-[10px] uppercase tracking-wide text-ink-subtle">
              Triage breakdown
            </span>
            <span className="text-[10px] text-ink-subtle">click per filtrare</span>
          </div>
          <div className="grid grid-cols-4 gap-2">
            {STATUS_DEF.map((s) => {
              const n = stats.status_breakdown[s.key] ?? 0;
              return (
                <button
                  key={s.status}
                  type="button"
                  onClick={() => onPickStatus(s.status)}
                  className="flex flex-col items-start gap-0.5 rounded p-2 text-left hover:bg-[var(--color-surface-hover)]"
                  title={`filtra per ${s.label.toLowerCase()}`}
                >
                  <span
                    className={
                      'inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[10px] font-medium ' +
                      s.tone
                    }
                  >
                    <Inbox size={10} />
                    {s.label}
                  </span>
                  <span className="text-lg font-semibold tabular-nums">{n}</span>
                </button>
              );
            })}
          </div>
        </div>

        <div className="rounded-lg bg-[var(--color-surface)] p-3 ring-1 ring-[var(--color-border)]">
          <div className="mb-2 flex items-center justify-between">
            <span className="text-[10px] uppercase tracking-wide text-ink-subtle">
              Documenti correlati a negativi
            </span>
            <span className="text-[10px] text-ink-subtle">
              {sourcesLoading ? '…' : `${sources.length} doc`}
            </span>
          </div>
          {sources.length === 0 ? (
            <p className="text-xs text-ink-subtle">
              Nessun documento con feedback ricorrenti nel periodo.
            </p>
          ) : (
            <ul className="space-y-1">
              {sources.slice(0, 5).map((s) => (
                <li
                  key={s.document_id}
                  className="flex items-center gap-2 text-[11px]"
                >
                  <span
                    className={
                      'inline-block w-10 shrink-0 rounded px-1 py-0.5 text-center font-mono tabular-nums ' +
                      (s.down_rate >= 0.5
                        ? 'bg-rose-500/15 text-rose-700 dark:text-rose-300'
                        : s.down_rate >= 0.25
                          ? 'bg-amber-500/15 text-amber-700 dark:text-amber-300'
                          : 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300')
                    }
                  >
                    {Math.round(s.down_rate * 100)}%
                  </span>
                  <span className="truncate" title={s.title}>
                    {s.title}
                  </span>
                  <span className="ml-auto shrink-0 font-mono text-[10px] text-ink-subtle">
                    {s.down}/{s.total}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </section>
  );
}
