import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { AnimatePresence, motion } from 'framer-motion';
import { toast } from 'sonner';
import {
  AlertTriangle,
  ChevronRight,
  Clock,
  Code2,
  Copy,
  CornerDownRight,
  Cpu,
  Database,
  Hash,
  Loader2,
  Play,
  Sparkles,
  Table2,
} from 'lucide-react';
import { api } from '../../lib/api.js';
import { useAppStore } from '../../store/app.js';
import { SqlBlock } from '../SqlBlock.js';
import { ResultTable } from '../ResultTable.js';
import { cn } from '../../lib/cn.js';
import type { ChatTurn } from './turn-types.js';
import { statusCopy } from './assistant-turn-status.js';
import { AssistantTurnHeader } from './AssistantTurnHeader.js';
import { AssistantTurnError } from './AssistantTurnError.js';

interface Props {
  turn: ChatTurn;
  connectionId: string;
  onRetry: () => void;
  /** Click handler for follow-up question chips. Sends a new turn. */
  onFollowUp?: (question: string) => void;
}

export function AssistantTurn({ turn, connectionId, onRetry, onFollowUp }: Props) {
  // Auto-open the query block when the executed query produced zero rows so
  // the user immediately sees what was actually run and can spot the mistake
  // (wrong label, narrow filter, etc.) without an extra click.
  const emptyResult = turn.result !== undefined && turn.result.rowCount === 0;
  const [showQuery, setShowQuery] = useState(emptyResult);
  const [showRows, setShowRows] = useState(true);
  const [localResult, setLocalResult] = useState(turn.result ?? null);

  const isWorking = turn.status !== 'ready' && turn.status !== 'error';

  const execute = useMutation({
    mutationFn: () => api.execute({ connectionId, query: turn.translation!.query, rowLimit: 100 }),
    onSuccess: (r) => {
      setLocalResult(r);
      setShowRows(true);
      toast.success(`${r.rowCount} rows in ${r.durationMs}ms`);
    },
    onError: (err: Error) => toast.error('Execution failed', { description: err.message }),
  });

  const result = localResult ?? turn.result ?? null;
  const setLastResponse = useAppStore((s) => s.setLastResponse);
  const locale = useAppStore((s) => s.responseLocale);
  const STATUS = statusCopy(locale);

  const copyQuery = () => {
    if (!turn.translation) return;
    navigator.clipboard.writeText(turn.translation.query);
    toast.success('Copied');
  };

  const focusGraph = () => {
    if (!turn.translation) return;
    setLastResponse(turn.translation);
    toast.success('Highlighted in schema');
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18 }}
      className="panel flex flex-col overflow-hidden shrink-0"
    >
      <AssistantTurnHeader turn={turn} isWorking={isWorking} statusCopy={STATUS} />

      {turn.status === 'error' && turn.error && (
        <AssistantTurnError message={turn.error} onRetry={onRetry} />
      )}

      {turn.summary && (
        <section className="border-b border-border-subtle px-3 py-3">
          <div className="flex items-start gap-3 rounded-lg border border-accent/15 bg-accent/5 px-3 py-3">
            <div
              className="mt-0.5 grid h-7 w-7 shrink-0 place-items-center rounded-md"
              style={{
                background: 'rgb(var(--accent) / 0.16)',
                color: 'rgb(var(--accent))',
              }}
            >
              <Sparkles className="h-3.5 w-3.5" />
            </div>
            <div className="min-w-0 flex-1 flex flex-col gap-2.5">
              <div className="text-[11px] font-semibold uppercase text-text-dim">Answer</div>
              <p className="whitespace-pre-wrap text-[14px] leading-[1.6] text-text">
                {turn.summary}
              </p>
              {turn.highlights && turn.highlights.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {turn.highlights.map((h, i) => (
                    <span
                      key={i}
                      className="inline-flex items-center px-2 py-1 rounded-md text-[11px] leading-tight text-text-muted"
                      style={{
                        background: 'rgb(var(--accent) / 0.08)',
                        border: '1px solid rgb(var(--accent) / 0.18)',
                      }}
                    >
                      {h}
                    </span>
                  ))}
                </div>
              )}
              {turn.followUps && turn.followUps.length > 0 && onFollowUp && (
                <div className="flex flex-wrap gap-1.5 mt-0.5">
                  {turn.followUps.map((q, i) => (
                    <button
                      key={i}
                      type="button"
                      onClick={() => onFollowUp(q)}
                      className="inline-flex items-center gap-1 px-2 h-6 rounded-md border text-[11px] text-text-muted hover:text-text transition-colors"
                      style={{
                        background: 'rgb(var(--surface-2) / 0.7)',
                        borderColor: 'rgb(var(--border-subtle))',
                      }}
                      title={locale === 'it' ? 'Chiedi questo' : 'Ask this follow-up'}
                    >
                      <CornerDownRight className="w-3 h-3 text-accent" />
                      <span className="truncate max-w-64">{q}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </section>
      )}

      {isWorking && !turn.summary && (
        <div className="flex items-center gap-2.5 border-b border-border-subtle bg-surface-2/25 px-3 py-3">
          <span className="typing-dots" aria-hidden>
            <span />
            <span />
            <span />
          </span>
          <span className="text-[12px] text-text-muted">{STATUS[turn.status]}</span>
        </div>
      )}

      {turn.executionError && (
        <div className="px-3 py-2.5 flex items-start gap-2 text-[12px] border-b border-border-subtle bg-warn/5">
          <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0 text-warn" />
          <div className="flex-1 min-w-0">
            <div className="font-semibold text-warn">Query generated but could not execute</div>
            <div className="text-[11px] text-text-muted mt-0.5 break-words">
              {turn.executionError.message}
            </div>
          </div>
          <button
            type="button"
            onClick={() => execute.mutate()}
            className="btn-ghost h-7 px-2"
            disabled={execute.isPending}
            aria-label="Try execution again"
          >
            {execute.isPending ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Play className="w-3.5 h-3.5" />
            )}
            Try
          </button>
        </div>
      )}

      {turn.translation && (
        <div className="border-b border-border-subtle">
          <button
            type="button"
            onClick={() => setShowQuery((v) => !v)}
            aria-expanded={showQuery}
            className="flex w-full items-center gap-1.5 px-3 py-2.5 text-left font-mono text-[11px] text-text-dim transition-colors hover:bg-surface-2/35 hover:text-text"
          >
            <motion.span
              animate={{ rotate: showQuery ? 90 : 0 }}
              transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] }}
              className="inline-flex"
            >
              <ChevronRight className="h-3 w-3" />
            </motion.span>
            <Code2 className="h-3 w-3" />
            <span>{turn.translation.language.toUpperCase()} query</span>
            {turn.translation.retries > 0 && (
              <span className="chip chip-warn h-5 text-[10px] ml-1">
                {turn.translation.retries} {turn.translation.retries === 1 ? 'retry' : 'retries'}
              </span>
            )}
            <span className="ml-auto text-[10px] text-text-dim">{showQuery ? 'Hide' : 'View'}</span>
          </button>
          <AnimatePresence initial={false}>
            {showQuery && (
              <motion.div
                key="query-body"
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
                className="overflow-hidden"
              >
                <div className="mx-3 mb-3 overflow-hidden rounded-lg border border-border-subtle">
                  <SqlBlock sql={turn.translation.query} />
                  {turn.translation.explanation && (
                    <p className="text-[11px] leading-relaxed text-text-muted px-3 py-2 border-t border-border-subtle">
                      {turn.translation.explanation}
                    </p>
                  )}
                  {turn.translation.joinNotes.length > 0 && (
                    <ul className="text-[11px] text-text-muted list-disc pl-7 pr-3 py-2 space-y-0.5 border-t border-border-subtle">
                      {turn.translation.joinNotes.map((n, i) => (
                        <li key={i}>{n}</li>
                      ))}
                    </ul>
                  )}
                  {turn.translation.warnings.length > 0 && (
                    <div className="flex flex-col gap-1 px-3 py-2 border-t border-border-subtle">
                      {turn.translation.warnings.map((w, i) => (
                        <div
                          key={i}
                          className={cn(
                            'text-[11px] px-2 py-1 rounded',
                            w.severity === 'error'
                              ? 'chip-danger'
                              : w.severity === 'warn'
                                ? 'chip-warn'
                                : 'chip',
                          )}
                        >
                          {w.message}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}

      {result && (
        <div className="border-b border-border-subtle">
          <button
            type="button"
            onClick={() => setShowRows((v) => !v)}
            aria-expanded={showRows}
            className="flex w-full items-center gap-1.5 px-3 py-2.5 text-left font-mono text-[11px] text-text-dim transition-colors hover:bg-surface-2/35 hover:text-text"
          >
            <motion.span
              animate={{ rotate: showRows ? 90 : 0 }}
              transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] }}
              className="inline-flex"
            >
              <ChevronRight className="h-3 w-3" />
            </motion.span>
            <Table2 className="h-3 w-3" />
            <span>Result preview</span>
            <span className="ml-auto flex items-center gap-2 text-text-muted">
              <span className="flex items-center gap-1">
                <Hash className="h-3 w-3" />
                {result.rowCount}
              </span>
              <span className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                {result.durationMs}ms
              </span>
            </span>
          </button>
          <AnimatePresence initial={false}>
            {showRows && (
              <motion.div
                key="rows-body"
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.22, ease: [0.22, 1, 0.36, 1] }}
                className="overflow-hidden"
              >
                <div className="mx-3 mb-3 max-h-[300px] overflow-auto rounded-lg border border-border-subtle">
                  <ResultTable result={result} embedded />
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}

      {turn.translation && (
        <div className="flex items-center justify-between gap-2 px-3 py-2.5">
          <div className="flex min-w-0 flex-wrap items-center gap-1.5 font-mono text-[10px] text-text-dim">
            <span className="inline-flex h-6 max-w-full items-center gap-1 rounded-md border border-border-subtle bg-surface-2/35 px-2">
              <Cpu className="h-3 w-3 shrink-0" />
              {turn.translation.provider}/{turn.translation.model}
            </span>
            {turn.translation.involvedEntities.length > 0 && (
              <span className="inline-flex h-6 max-w-[220px] items-center gap-1 truncate rounded-md border border-border-subtle bg-surface-2/35 px-2">
                <Database className="h-3 w-3 shrink-0" />
                <span className="truncate">{turn.translation.involvedEntities.join(', ')}</span>
              </span>
            )}
            {turn.totalDurationMs !== undefined && (
              <span className="inline-flex h-6 items-center gap-1 rounded-md border border-border-subtle bg-surface-2/35 px-2">
                <Clock className="h-3 w-3" />
                {turn.totalDurationMs}ms total
              </span>
            )}
          </div>
          <div className="flex items-center gap-1 shrink-0">
            <button
              type="button"
              onClick={focusGraph}
              className="btn-ghost h-7 px-2"
              title="Focus in schema"
              aria-label="Focus in schema"
            >
              <Database className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              onClick={copyQuery}
              className="btn-ghost h-7 px-2"
              title="Copy query"
              aria-label="Copy query"
            >
              <Copy className="h-3.5 w-3.5" />
            </button>
            <button
              type="button"
              onClick={() => execute.mutate()}
              disabled={execute.isPending}
              className="btn-ghost h-7 px-2"
              title="Run again"
              aria-label="Run again"
            >
              {execute.isPending ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
              ) : (
                <Play className="h-3.5 w-3.5" />
              )}
            </button>
          </div>
        </div>
      )}
    </motion.div>
  );
}
