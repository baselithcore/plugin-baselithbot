import { AnimatePresence, motion } from 'framer-motion';
import { Brain, ChevronDown } from 'lucide-react';
import { useState } from 'react';
import { useElapsed } from '../../hooks/useElapsed';
import { cn } from '../../lib/cn';
import { duration, ease } from '../../lib/motion';

export interface ThinkingStep {
  agent?: string;
  step?: string;
  at?: number;
}

interface Props {
  trace: ThinkingStep[];
  streaming: boolean;
  startedAt?: number;
  firstTokenAt?: number;
  completedAt?: number;
}

function formatElapsed(ms: number): string {
  if (ms < 1000) return `${ms} ms`;
  const s = ms / 1000;
  if (s < 10) return `${s.toFixed(1)}s`;
  if (s < 60) return `${Math.round(s)}s`;
  const m = Math.floor(s / 60);
  return `${m}m ${Math.round(s - m * 60)}s`;
}

function stepLabel(step: ThinkingStep): string {
  return step.agent ?? step.step ?? '';
}

/**
 * Chain-of-thought panel rendered during streaming. Compact-by-default
 * pattern (Claude.ai / ChatGPT style):
 *
 *  - collapsed: brand-tinted pulse + "Sto pensando", elapsed time,
 *    truncated current step, chevron toggle showing step count
 *  - expanded: full chronological trace with dot timeline; latest step
 *    pulses in brand color, prior steps fade to subtle ink
 *
 * Auto-hides once the assistant emits the first token (CoT becomes
 * noise once the answer is flowing). Reduced-motion fallbacks: no
 * pulse, no layout animations.
 *
 * Replaces the legacy "last-3 trace lines" inline strip in Message.tsx.
 */
export function ThinkingPanel({
  trace,
  streaming,
  startedAt,
  firstTokenAt,
  completedAt,
}: Props) {
  const [expanded, setExpanded] = useState(false);
  const elapsedMs = useElapsed(startedAt, streaming, completedAt);

  if (!streaming || trace.length === 0) return null;

  // Once the first token arrives the answer takes over — keep the
  // panel only while the model is still thinking. Avoids cluttering
  // the chat once prose is streaming below.
  const thinking = !firstTokenAt;
  const current = trace[trace.length - 1];

  return (
    <motion.div
      layout="position"
      initial={{ opacity: 0, y: -4 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4 }}
      transition={{ duration: duration.base, ease: ease.outQuart }}
      className="mb-3 overflow-hidden rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)]"
    >
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="focus-ring flex w-full items-center gap-2.5 px-3 py-2 text-left hover:bg-[var(--color-canvas-raised)]"
        aria-expanded={expanded}
        aria-label={expanded ? 'nascondi ragionamento' : 'mostra ragionamento'}
      >
        {thinking ? <ThinkingIndicator /> : <DoneIndicator />}
        <div className="min-w-0 flex-1">
          <div className="flex items-baseline gap-1.5 text-[11.5px] font-semibold text-ink">
            <span>{thinking ? 'Sto pensando' : 'Generando la risposta'}</span>
            {elapsedMs > 0 && (
              <span className="text-[10px] font-normal tabular-nums text-ink-subtle">
                · {formatElapsed(elapsedMs)}
              </span>
            )}
          </div>
          {!expanded && current && (
            <AnimatePresence initial={false} mode="popLayout">
              <motion.div
                key={`thinking-current-${trace.length}`}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                transition={{ duration: duration.fast, ease: ease.outQuart }}
                className="truncate text-[10.5px] leading-snug text-ink-subtle"
              >
                {stepLabel(current)}
              </motion.div>
            </AnimatePresence>
          )}
        </div>
        <span className="inline-flex shrink-0 items-center gap-1 text-[10px] text-ink-subtle">
          <span className="inline-flex items-center gap-1 rounded-full border border-[var(--color-border)] bg-[var(--color-canvas)] px-1.5 py-0.5 tabular-nums">
            <Brain size={9} aria-hidden /> {trace.length}
          </span>
          <ChevronDown
            size={12}
            aria-hidden
            className={cn('transition-transform duration-200', expanded && 'rotate-180')}
          />
        </span>
      </button>

      <AnimatePresence initial={false}>
        {expanded && (
          <motion.div
            key="trace-expanded"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: duration.base, ease: ease.outQuart }}
            className="overflow-hidden border-t border-[var(--color-border)]/70"
          >
            <ol className="flex flex-col gap-1.5 px-3 py-2.5">
              {trace.map((t, i) => {
                const isLast = i === trace.length - 1;
                return (
                  <li
                    key={`trace-step-${i}-${t.at ?? ''}`}
                    className={cn(
                      'flex items-start gap-2 text-[11px] leading-snug',
                      isLast ? 'text-ink' : 'text-ink-subtle'
                    )}
                  >
                    <span
                      aria-hidden
                      className={cn(
                        'mt-1.5 size-1.5 shrink-0 rounded-full',
                        isLast
                          ? 'bg-[var(--color-brand)] motion-safe:animate-pulse'
                          : 'bg-[var(--color-border)]'
                      )}
                    />
                    {t.agent ? (
                      <span className="font-medium">{t.agent}</span>
                    ) : (
                      <span>{t.step}</span>
                    )}
                  </li>
                );
              })}
            </ol>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

function ThinkingIndicator() {
  return (
    <span className="relative grid size-5 shrink-0 place-items-center" aria-hidden>
      <span
        className="absolute inset-0 rounded-full bg-[var(--color-brand)] opacity-20 motion-safe:animate-ping"
        style={{ animationDuration: '1.6s' }}
      />
      <span className="relative size-2 rounded-full bg-[var(--color-brand)] shadow-[0_0_10px_var(--color-brand-ring,transparent)]" />
    </span>
  );
}

function DoneIndicator() {
  return (
    <span
      className="grid size-5 shrink-0 place-items-center rounded-full bg-[var(--color-brand-soft)]"
      aria-hidden
    >
      <Brain size={11} className="text-[var(--color-brand)]" />
    </span>
  );
}
