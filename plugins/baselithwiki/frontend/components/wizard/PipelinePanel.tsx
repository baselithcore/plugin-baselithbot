import { AnimatePresence, motion } from 'framer-motion';
import { AlertCircle, CheckCircle2, Copy, Loader2, Terminal } from 'lucide-react';
import { cn } from '../../lib/cn';
import { duration, ease } from '../../lib/motion';
import { Button, IconButton } from '../ui';
import type { DoneState, IngestSnapshot } from './pipeline-types';

export function PipelinePanel({
  state,
  expectedDocs,
  ingest,
  pct,
  cmd,
  copied,
  onCopy,
  onRetry,
}: {
  state: DoneState;
  expectedDocs: number;
  ingest: IngestSnapshot;
  pct: number;
  cmd: string;
  copied: boolean;
  onCopy: () => void;
  onRetry: () => void;
}) {
  // Phase derivation drives the visible step indicator.
  const phases: Array<{ id: DoneState; label: string }> = [
    { id: 'sending', label: 'Avvio servizio' },
    { id: 'waiting', label: 'Preparazione' },
    ...(expectedDocs > 0
      ? ([{ id: 'ingesting', label: 'Elaborazione documenti' }] as Array<{
          id: DoneState;
          label: string;
        }>)
      : []),
    { id: 'all_done', label: 'Pronto' },
  ];
  const orderIdx =
    state === 'manual_required'
      ? phases.findIndex((p) => p.id === 'sending')
      : phases.findIndex((p) => p.id === state);

  return (
    <section
      className="rounded-lg border border-[var(--color-border)] bg-[var(--color-canvas)] p-3 space-y-3"
      role="status"
      aria-live="polite"
    >
      {/* phase stepper */}
      <ol className="flex items-center gap-1.5 flex-wrap text-[10.5px]">
        {phases.map((p, i) => {
          const passed = i < orderIdx || state === 'all_done';
          const current = i === orderIdx && state !== 'all_done';
          const errored = (state === 'error' || state === 'manual_required') && i === orderIdx;
          // Tick scales in when current/passed/errored state flips.
          // Animate the badge contents, not the pill — keeps layout stable.
          const badgeKey = errored ? 'err' : passed ? 'ok' : current ? 'cur' : 'idle';
          return (
            <li key={p.id} className="flex items-center gap-1.5">
              <motion.span
                animate={current ? { scale: [1, 1.06, 1] } : { scale: 1 }}
                transition={{
                  duration: current ? duration.slow : duration.fast,
                  ease: ease.outQuart,
                }}
                className={cn(
                  'inline-flex items-center justify-center rounded-full size-4 text-[9px] font-semibold border transition-colors',
                  errored
                    ? 'bg-[var(--color-danger)] text-white border-[var(--color-danger)]'
                    : current
                      ? 'bg-[var(--color-brand)] text-white border-[var(--color-brand)]'
                      : passed
                        ? 'bg-[var(--color-success)]/15 text-[var(--color-success)] border-[var(--color-success)]/40'
                        : 'bg-[var(--color-surface)] text-ink-subtle border-[var(--color-border)]'
                )}
                style={{ transitionDuration: `${duration.fast * 1000}ms` }}
              >
                <AnimatePresence mode="wait" initial={false}>
                  <motion.span
                    key={badgeKey}
                    initial={{ opacity: 0, scale: 0.7 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.7 }}
                    transition={{ duration: duration.fast, ease: ease.outExpo }}
                    className="inline-flex items-center justify-center"
                  >
                    {errored ? '!' : passed ? <CheckCircle2 size={9} /> : i + 1}
                  </motion.span>
                </AnimatePresence>
              </motion.span>
              <span
                className={cn(
                  current ? 'font-semibold text-ink' : 'text-ink-subtle',
                  errored && 'text-[var(--color-danger)]'
                )}
              >
                {p.label}
              </span>
              {i < phases.length - 1 && <span className="mx-1 h-px w-4 bg-[var(--color-border)]" />}
            </li>
          );
        })}
      </ol>

      {/* status message + spinner */}
      <div className="flex items-start gap-2.5">
        {state === 'all_done' ? (
          <CheckCircle2 size={14} className="text-[var(--color-success)] shrink-0 mt-0.5" />
        ) : state === 'error' || state === 'manual_required' ? (
          <AlertCircle size={14} className="text-[var(--color-danger)] shrink-0 mt-0.5" />
        ) : (
          <Loader2 size={14} className="animate-spin text-[var(--color-brand)] shrink-0 mt-0.5" />
        )}
        <div className="min-w-0 flex-1">
          <div className="text-[12px] font-semibold">
            {state === 'sending' && 'Configurazione applicata, avvio in corso…'}
            {state === 'waiting' && 'Attendo il servizio…'}
            {state === 'ingesting' &&
              (expectedDocs > 0
                ? `Elaborazione ${ingest.done + ingest.errors}/${ingest.total} documenti`
                : 'Servizio pronto')}
            {state === 'all_done' &&
              (expectedDocs > 0
                ? `Elaborazione completata · ${ingest.done} pagine generate${ingest.errors > 0 ? `, ${ingest.errors} con errori` : ''}`
                : 'Tutto pronto.')}
            {state === 'error' && 'Qualcosa è andato storto.'}
            {state === 'manual_required' && 'Riavvio manuale richiesto.'}
          </div>
          <div className="text-[10.5px] leading-relaxed text-ink-muted">
            {state === 'sending' && 'La configurazione è stata salvata. Ora la stiamo attivando.'}
            {state === 'waiting' &&
              'Il dominio viene caricato e i servizi di ricerca vengono preparati.'}
            {state === 'ingesting' &&
              expectedDocs > 0 &&
              'I documenti vengono trasformati in pagine consultabili.'}
            {state === 'all_done' &&
              expectedDocs > 0 &&
              'La wiki è pronta: puoi iniziare a interrogare le fonti caricate.'}
            {state === 'error' &&
              'Il riavvio automatico non è andato a buon fine. Esegui il comando qui sotto e premi «Riprova».'}
            {state === 'manual_required' &&
              'Il server è in esecuzione senza --reload e senza supervisor: il restart automatico ucciderebbe il processo. Esegui il comando qui sotto in un terminale e ricarica.'}
          </div>
        </div>
      </div>

      {/* ingest progress bar (during + after ingestion) */}
      {(state === 'ingesting' || (state === 'all_done' && expectedDocs > 0)) && (
        <>
          <div
            className="h-1.5 w-full rounded-full bg-[var(--color-surface)] overflow-hidden"
            aria-label="progresso ingestion"
            role="progressbar"
            aria-valuenow={pct}
            aria-valuemin={0}
            aria-valuemax={100}
          >
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${pct}%` }}
              transition={{ duration: duration.slow, ease: ease.outExpo }}
              className={cn(
                'h-full',
                ingest.errors > 0 && pct === 100
                  ? 'bg-[var(--color-warning)] transition-colors duration-200'
                  : 'bg-[var(--color-brand)]'
              )}
            />
          </div>

          {ingest.files.length > 0 && (
            <motion.ul
              className="rounded-md border border-[var(--color-border)] divide-y divide-[var(--color-border)] max-h-44 overflow-y-auto"
              initial="hidden"
              animate="visible"
              variants={{
                visible: { transition: { staggerChildren: 0.035 } },
                hidden: {},
              }}
            >
              {ingest.files.map((f) => (
                <motion.li
                  key={f.filename}
                  layout="position"
                  variants={{
                    hidden: { opacity: 0, y: 4 },
                    visible: { opacity: 1, y: 0 },
                  }}
                  transition={{ duration: duration.base, ease: ease.outQuart }}
                  className="flex items-center gap-2 px-2.5 py-1.5 text-[11px]"
                >
                  <FileStatusIcon status={f.status} />
                  <span className="flex-1 truncate font-mono">{f.filename}</span>
                  <span className="text-[10px] text-ink-subtle tabular-nums">
                    {f.status === 'done'
                      ? `${f.pages_written} pag.`
                      : f.status === 'error'
                        ? 'errore'
                        : f.status}
                  </span>
                </motion.li>
              ))}
            </motion.ul>
          )}
        </>
      )}

      {(state === 'error' || state === 'manual_required') && (
        <div className="space-y-2 rounded-md border border-[var(--color-danger)]/30 bg-[var(--color-danger)]/5 px-3 py-2">
          <p className="text-[10.5px] leading-relaxed text-ink-muted">
            {state === 'manual_required'
              ? 'Esegui questo comando in un terminale, poi ricarica la pagina:'
              : 'Esegui questo comando in un terminale, poi premi «Riprova»:'}
          </p>
          <div className="flex items-center gap-2">
            <code className="flex-1 break-all rounded border border-[var(--color-border)] bg-[var(--color-canvas)] px-2 py-1 font-mono text-[11px]">
              {cmd}
            </code>
            <IconButton
              icon={copied ? CheckCircle2 : Copy}
              aria-label="copia comando"
              size="sm"
              onClick={onCopy}
            />
            <Button leadingIcon={Terminal} onClick={onRetry}>
              Riprova
            </Button>
          </div>
        </div>
      )}
    </section>
  );
}

function FileStatusIcon({ status }: { status: 'queued' | 'running' | 'done' | 'error' }) {
  if (status === 'done')
    return <CheckCircle2 size={12} className="text-[var(--color-success)] shrink-0" />;
  if (status === 'error')
    return <AlertCircle size={12} className="text-[var(--color-danger)] shrink-0" />;
  return <Loader2 size={12} className="animate-spin text-[var(--color-brand)] shrink-0" />;
}
