import { AlertCircle, CheckCircle2, ChevronDown, Loader2, RefreshCw } from 'lucide-react';
import { useState } from 'react';
import type { IngestJob, IngestStreamEvent } from '../../lib/types';
import { cn } from '../../lib/cn';
import { Button } from '../ui';

const STATUS_LABEL: Record<IngestJob['status'], string> = {
  queued: 'in coda',
  running: 'in corso',
  done: 'completato',
  error: 'errore',
};

export function JobCard({
  job,
  compact = false,
  onRetry,
}: {
  job: IngestJob;
  compact?: boolean;
  onRetry?: (job: IngestJob) => void;
}) {
  const total = job.pages_written + job.pages_needs_review + job.pages_conflict + job.pages_error;
  const showRetry = onRetry && (job.status === 'error' || job.pages_error > 0);

  return (
    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-canvas)] p-3">
      <div className="flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <StatusIcon status={job.status} />
          <div className="min-w-0">
            <div className="truncate text-[12.5px] font-medium">{job.filename}</div>
            <div className="font-mono text-[10px] tabular-nums text-ink-subtle">
              {new Date(job.created_at * 1000).toLocaleString('it-IT', {
                day: '2-digit',
                month: '2-digit',
                hour: '2-digit',
                minute: '2-digit',
              })}
              {job.backend && ` · ${job.backend}`}
            </div>
          </div>
        </div>
        <StatusBadge status={job.status} />
      </div>

      {!compact && job.summary && (
        <div className="mt-1.5 text-[10.5px] text-ink-muted">{job.summary}</div>
      )}

      {total > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          <PageStat label="generate" value={job.pages_written} tone="brand" />
          {job.pages_needs_review > 0 && (
            <PageStat label="da rivedere" value={job.pages_needs_review} tone="warning" />
          )}
          {job.pages_conflict > 0 && (
            <PageStat label="conflitti" value={job.pages_conflict} tone="warning" />
          )}
          {job.pages_error > 0 && <PageStat label="errori" value={job.pages_error} tone="danger" />}
        </div>
      )}

      {!compact && job.errors && job.errors.length > 0 && <ErrorList errors={job.errors} />}

      {showRetry && (
        <div className="mt-2.5 flex justify-end">
          <Button
            size="sm"
            variant="secondary"
            leadingIcon={RefreshCw}
            onClick={() => onRetry!(job)}
          >
            Riprova
          </Button>
        </div>
      )}
    </div>
  );
}

function PageStat({
  label,
  value,
  tone,
}: {
  label: string;
  value: number;
  tone: 'brand' | 'warning' | 'danger';
}) {
  const cls =
    tone === 'brand'
      ? 'bg-[var(--color-brand-soft)] text-[var(--color-brand-contrast)] border-[var(--color-brand-ring)]'
      : tone === 'warning'
        ? 'bg-amber-500/10 text-amber-700 dark:text-amber-300 border-amber-500/30'
        : 'bg-rose-500/10 text-rose-700 dark:text-rose-300 border-rose-500/30';
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[10px] font-medium',
        cls
      )}
    >
      <span className="tabular-nums">{value}</span>
      {label}
    </span>
  );
}

function ErrorList({ errors }: { errors: NonNullable<IngestJob['errors']> }) {
  const [open, setOpen] = useState(false);
  if (errors.length === 0) return null;
  return (
    <details
      open={open}
      onToggle={(e) => setOpen((e.currentTarget as HTMLDetailsElement).open)}
      className="mt-2 rounded-md border border-rose-500/30 bg-rose-500/5"
    >
      <summary className="cursor-pointer list-none px-2 py-1 text-[10.5px] font-semibold text-rose-700 dark:text-rose-300 flex items-center gap-1.5">
        <ChevronDown
          size={11}
          className={cn('transition-transform', open && 'rotate-180')}
          aria-hidden
        />
        {errors.length} {errors.length === 1 ? 'errore' : 'errori'} riscontrat
        {errors.length === 1 ? 'o' : 'i'}
      </summary>
      <ul className="border-t border-rose-500/20 px-2 py-1 space-y-0.5 text-[10.5px] text-rose-700 dark:text-rose-300">
        {errors.slice(0, 8).map((e, i) => (
          <li key={i} className="truncate">
            {String(e)}
          </li>
        ))}
        {errors.length > 8 && (
          <li className="text-[9.5px] italic text-ink-subtle">… e altri {errors.length - 8}</li>
        )}
      </ul>
    </details>
  );
}

function StatusIcon({ status }: { status: IngestJob['status'] }) {
  if (status === 'running' || status === 'queued')
    return <Loader2 size={13} className="animate-spin text-[var(--color-brand)]" aria-hidden />;
  if (status === 'done') return <CheckCircle2 size={13} className="text-emerald-500" aria-hidden />;
  return <AlertCircle size={13} className="text-rose-500" aria-hidden />;
}

function StatusBadge({ status }: { status: IngestJob['status'] }) {
  const style =
    status === 'done'
      ? 'bg-emerald-500/15 text-emerald-700 dark:text-emerald-300'
      : status === 'error'
        ? 'bg-rose-500/15 text-rose-700 dark:text-rose-300'
        : 'bg-[var(--color-brand-soft)] text-[var(--color-brand-contrast)]';
  return (
    <span
      className={cn(
        'shrink-0 rounded-full px-2 py-[2px] text-[10px] font-semibold uppercase tracking-wide',
        style
      )}
    >
      {STATUS_LABEL[status]}
    </span>
  );
}

const PHASE_ORDER = [
  'extract',
  'classify',
  'plan',
  'generate',
  'lint',
  'critic',
  'index',
  'final',
] as const;

const PHASE_LABEL: Record<string, string> = {
  extract: 'Estrazione',
  classify: 'Classificazione',
  plan: 'Pianificazione',
  generate: 'Generazione',
  lint: 'Verifica',
  critic: 'Revisione',
  index: 'Indicizzazione',
  final: 'Finalizzazione',
  status: 'Stato',
  page: 'Pagina',
  log: 'Log',
};

/**
 * Friendly streaming timeline. Groups raw NDJSON events into named phases
 * and surfaces the latest message per phase, plus a tail of page writes
 * for traceability.
 */
export function EventTimeline({ events }: { events: IngestStreamEvent[] }) {
  const phaseLatest = new Map<string, { message: string; t: number; level?: string }>();
  const pageEvents: Array<Extract<IngestStreamEvent, { type: 'page' }>> = [];

  for (const ev of events) {
    if (ev.type === 'page') {
      pageEvents.push(ev);
    } else if (ev.type === 'log') {
      const key = ev.phase || 'log';
      phaseLatest.set(key, { message: ev.message, t: ev.t, level: ev.level });
    } else if (ev.type === 'status') {
      phaseLatest.set('status', { message: ev.message ?? ev.status, t: ev.t });
    }
  }

  const seenPhases = Array.from(phaseLatest.keys());
  const orderedPhases = [
    ...PHASE_ORDER.filter((p) => seenPhases.includes(p)),
    ...seenPhases.filter((p) => !PHASE_ORDER.includes(p as (typeof PHASE_ORDER)[number])),
  ];

  if (events.length === 0) {
    return (
      <div className="mt-3 rounded-lg border border-dashed border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-2 text-[11px] text-ink-subtle">
        In attesa dei primi eventi…
      </div>
    );
  }

  return (
    <div
      className="mt-3 max-h-72 overflow-y-auto rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)]"
      role="log"
      aria-live="polite"
      aria-label="cronologia eventi pipeline"
    >
      {orderedPhases.length > 0 && (
        <ul className="divide-y divide-[var(--color-border)]">
          {orderedPhases.map((phase) => {
            const last = phaseLatest.get(phase)!;
            const errored = last.level === 'error' || last.level === 'critical';
            return (
              <li key={phase} className="flex items-start gap-2 px-3 py-1.5 text-[11px]">
                <span
                  className={cn(
                    'mt-1 inline-block size-1.5 shrink-0 rounded-full',
                    errored
                      ? 'bg-rose-500'
                      : phase === 'final'
                        ? 'bg-emerald-500'
                        : 'bg-[var(--color-brand)]'
                  )}
                  aria-hidden
                />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold text-ink">{PHASE_LABEL[phase] ?? phase}</span>
                    <span className="font-mono text-[9.5px] tabular-nums text-ink-subtle">
                      {new Date(last.t * 1000).toLocaleTimeString('it-IT')}
                    </span>
                  </div>
                  <div className="truncate text-[10.5px] text-ink-muted">{last.message}</div>
                </div>
              </li>
            );
          })}
        </ul>
      )}
      {pageEvents.length > 0 && (
        <details open className="border-t border-[var(--color-border)]">
          <summary className="cursor-pointer list-none px-3 py-1.5 text-[10.5px] font-semibold uppercase text-ink-subtle">
            Pagine scritte ({pageEvents.length})
          </summary>
          <ul className="divide-y divide-[var(--color-border)] border-t border-[var(--color-border)]">
            {pageEvents.slice(-12).map((ev, i) => (
              <PageRow key={i} ev={ev} />
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}

function PageRow({ ev }: { ev: Extract<IngestStreamEvent, { type: 'page' }> }) {
  const color =
    ev.status === 'written'
      ? 'text-emerald-600 dark:text-emerald-400'
      : ev.status === 'error'
        ? 'text-rose-600 dark:text-rose-400'
        : 'text-amber-600 dark:text-amber-400';
  return (
    <li className="px-3 py-1 text-[10.5px]">
      <div className="flex items-center gap-2">
        <span className={cn('font-semibold uppercase', color)}>{ev.status}</span>
        <span className="truncate font-mono text-ink">{ev.path}</span>
        <span className="ml-auto shrink-0 text-[9.5px] tabular-nums text-ink-subtle">
          {ev.iterations} iter · {(ev.bytes / 1024).toFixed(1)} KB
        </span>
      </div>
    </li>
  );
}
