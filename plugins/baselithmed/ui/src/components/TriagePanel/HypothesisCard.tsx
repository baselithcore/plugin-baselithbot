import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronDown, ChevronRight } from 'lucide-react';
import clsx from 'clsx';
import type { DifferentialHypothesis } from '../../lib/types';

export function HypothesisCard({
  hypothesis,
  rank,
}: {
  hypothesis: DifferentialHypothesis;
  rank: number;
}) {
  const [open, setOpen] = useState(rank === 1);
  const pct = Math.round(hypothesis.confidence * 100);
  return (
    <li className="overflow-hidden rounded-xl border border-ink-200/70 bg-white/80 dark:border-ink-700/60 dark:bg-surface-dark-raised/70">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-start gap-3 px-3.5 py-3 text-left transition hover:bg-ink-50/80 dark:hover:bg-surface-dark-sunken/40"
        aria-expanded={open}
      >
        <span className="num grid h-7 w-7 shrink-0 place-items-center rounded-lg bg-ink-100 text-2xs font-semibold text-ink-600 dark:bg-ink-700/50 dark:text-ink-200">
          {rank}
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="truncate text-sm font-semibold text-ink-800 dark:text-ink-50">
              {hypothesis.condition}
            </span>
            {hypothesis.icd10 && <span className="pill-mono">ICD {hypothesis.icd10}</span>}
          </div>
          <ConfidenceBar value={hypothesis.confidence} pct={pct} />
        </div>
        {open ? (
          <ChevronDown className="mt-1 h-4 w-4 shrink-0 text-ink-400" aria-hidden />
        ) : (
          <ChevronRight className="mt-1 h-4 w-4 shrink-0 text-ink-400" aria-hidden />
        )}
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            layout
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.18 }}
            className="border-t border-ink-200/70 px-3.5 py-3 text-xs dark:border-ink-700/60"
          >
            <div className="grid grid-cols-2 gap-3">
              <FindingsBlock
                title="A favore"
                tone="positive"
                items={hypothesis.supporting_findings}
              />
              <FindingsBlock
                title="Contro"
                tone="negative"
                items={hypothesis.contradicting_findings}
              />
            </div>
            {hypothesis.recommended_workup.length > 0 && (
              <div className="mt-3">
                <div className="section-title mb-1.5">Workup raccomandato</div>
                <ul className="space-y-1">
                  {hypothesis.recommended_workup.map((w, i) => (
                    <li key={i} className="flex items-start gap-1.5 text-ink-700 dark:text-ink-100">
                      <span className="mt-1.5 h-1 w-1 shrink-0 rounded-full bg-accent-500" />
                      <span>{w}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {hypothesis.p_value_simulated !== null && (
              <div className="mt-3 flex items-center justify-between rounded-lg bg-surface-sunken/50 px-3 py-2 text-2xs text-ink-500 dark:bg-surface-dark-sunken/40 dark:text-ink-300">
                <span className="font-medium uppercase tracking-[0.12em]">p-value simulato</span>
                <span className="num font-mono text-xs">
                  {hypothesis.p_value_simulated.toFixed(3)}
                </span>
              </div>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </li>
  );
}

function FindingsBlock({
  title,
  tone,
  items,
}: {
  title: string;
  tone: 'positive' | 'negative';
  items: string[];
}) {
  if (!items.length) {
    return (
      <div>
        <div className="section-title mb-1.5">{title}</div>
        <p className="text-2xs italic text-ink-400">—</p>
      </div>
    );
  }
  return (
    <div>
      <div className="section-title mb-1.5">{title}</div>
      <ul className="space-y-1">
        {items.map((s, i) => (
          <li key={i} className="flex items-start gap-1.5 text-ink-700 dark:text-ink-100">
            <span
              className={clsx(
                'mt-1.5 h-1 w-1 shrink-0 rounded-full',
                tone === 'positive' ? 'bg-triage-green' : 'bg-triage-red'
              )}
              aria-hidden
            />
            <span>{s}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function ConfidenceBar({ value, pct }: { value: number; pct: number }) {
  return (
    <div className="mt-1.5 flex items-center gap-2.5">
      <div
        className="h-1 flex-1 overflow-hidden rounded-full bg-ink-100 dark:bg-ink-700/50"
        role="progressbar"
        aria-valuenow={pct}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${Math.min(100, Math.max(0, value * 100))}%` }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          className="h-full rounded-full bg-gradient-to-r from-accent-500 to-accent-700"
        />
      </div>
      <span className="num w-12 text-right font-mono text-2xs font-semibold text-ink-600 dark:text-ink-100">
        {pct}%
      </span>
    </div>
  );
}
