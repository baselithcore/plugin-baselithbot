import { motion } from 'framer-motion';
import { Activity, MapPin, Timer, Database, MinusCircle } from 'lucide-react';
import clsx from 'clsx';
import type { Symptom } from '../lib/types';

interface Props {
  symptoms: Symptom[];
  deniedSymptoms?: string[];
}

export function SymptomMatrixPanel({ symptoms, deniedSymptoms = [] }: Props) {
  const isEmpty = symptoms.length === 0 && deniedSymptoms.length === 0;
  return (
    <aside className="surface flex h-full flex-col overflow-hidden" aria-label="Symptom Matrix">
      <header className="flex items-center justify-between border-b border-ink-200/70 px-5 py-3.5 dark:border-ink-700/60">
        <div className="flex items-center gap-2.5">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-ink-100/80 text-ink-600 dark:bg-ink-700/40 dark:text-ink-200">
            <Database className="h-4 w-4" aria-hidden />
          </span>
          <div className="leading-tight">
            <h2 className="font-display text-sm font-semibold tracking-tight">Symptom Matrix</h2>
            <p className="text-2xs uppercase tracking-[0.14em] text-ink-400">
              Soggettivo · paziente
            </p>
          </div>
        </div>
        <span className="pill-mono num">
          {symptoms.length}/{symptoms.length === 0 ? '—' : symptoms.length}
        </span>
      </header>

      <div className="scroll-fade flex-1 overflow-y-auto px-3 py-3">
        {isEmpty ? (
          <EmptyState />
        ) : (
          <>
            {symptoms.length > 0 && (
              <ul className="space-y-1.5" role="list">
                {symptoms.map((s, i) => (
                  <SymptomRow key={`${s.canonical_name}-${i}`} symptom={s} index={i} />
                ))}
              </ul>
            )}
            {deniedSymptoms.length > 0 && <DeniedSection items={deniedSymptoms} />}
          </>
        )}
      </div>
    </aside>
  );
}

function DeniedSection({ items }: { items: string[] }) {
  return (
    <section
      aria-label="Sintomi negati"
      className="mt-3 rounded-xl border border-ink-200/70 bg-surface-sunken/50 p-3 dark:border-ink-700/60 dark:bg-surface-dark-sunken/30"
    >
      <header className="mb-2 flex items-center gap-2">
        <MinusCircle className="h-3.5 w-3.5 text-ink-400 dark:text-ink-300" aria-hidden />
        <h3 className="text-2xs font-semibold uppercase tracking-[0.12em] text-ink-500 dark:text-ink-200">
          Pertinent negatives ({items.length})
        </h3>
      </header>
      <ul className="flex flex-wrap gap-1.5" role="list">
        {items.map((d) => (
          <li
            key={d}
            className="pill border-ink-200/70 bg-white/60 text-ink-500 line-through decoration-ink-300 dark:border-ink-700/60 dark:bg-surface-dark-raised/40 dark:text-ink-300"
          >
            {d}
          </li>
        ))}
      </ul>
      <p className="mt-2 text-2xs leading-relaxed text-ink-400">
        Il paziente nega esplicitamente questi sintomi: usati come contradicting findings nella DDx.
      </p>
    </section>
  );
}

function SymptomRow({ symptom, index }: { symptom: Symptom; index: number }) {
  const hasMeta =
    symptom.body_site || symptom.onset || symptom.icd10_hint || symptom.character.length > 0;

  return (
    <motion.li
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: Math.min(index * 0.03, 0.18) }}
      className="group rounded-xl border border-transparent px-3 py-2.5 transition hover:border-ink-200/70 hover:bg-white/60 dark:hover:border-ink-700/60 dark:hover:bg-surface-dark-raised/40"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="truncate text-sm font-medium text-ink-800 dark:text-ink-50">
              {symptom.canonical_name}
            </span>
            {symptom.icd10_hint && <span className="pill-mono">ICD {symptom.icd10_hint}</span>}
          </div>
          {symptom.raw_quote && (
            <p className="mt-0.5 line-clamp-2 text-xs italic text-ink-400">"{symptom.raw_quote}"</p>
          )}
        </div>
        {symptom.severity_nrs !== null && <SeverityCell value={symptom.severity_nrs} />}
      </div>
      {hasMeta && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {symptom.body_site && (
            <span className="pill">
              <MapPin className="h-3 w-3" aria-hidden />
              {symptom.body_site}
            </span>
          )}
          {symptom.onset && (
            <span className="pill num">
              <Timer className="h-3 w-3" aria-hidden />
              {formatOnset(symptom.onset)}
            </span>
          )}
          {symptom.character.slice(0, 3).map((c) => (
            <span key={c} className="pill">
              {c}
            </span>
          ))}
        </div>
      )}
    </motion.li>
  );
}

function SeverityCell({ value }: { value: number }) {
  return (
    <div className="flex shrink-0 items-center gap-2" aria-label={`Severità NRS ${value} su 10`}>
      <SeverityBars value={value} />
      <div className="text-right leading-none">
        <div
          className={clsx(
            'num font-display text-base font-semibold tracking-tight',
            value >= 8
              ? 'text-triage-red'
              : value >= 5
                ? 'text-triage-yellow-ink dark:text-triage-yellow'
                : 'text-accent-700 dark:text-accent-300'
          )}
        >
          {value}
        </div>
        <div className="mt-0.5 text-2xs font-medium uppercase tracking-[0.1em] text-ink-400">
          NRS
        </div>
      </div>
    </div>
  );
}

function SeverityBars({ value }: { value: number }) {
  const bars = 10;
  return (
    <div className="flex items-end gap-0.5" aria-hidden>
      {Array.from({ length: bars }).map((_, i) => {
        const active = i < value;
        const h = 4 + i * 1.2;
        return (
          <span
            key={i}
            style={{ height: `${h}px` }}
            className={clsx(
              'w-1 rounded-sm transition-colors',
              active
                ? value >= 8
                  ? 'bg-triage-red'
                  : value >= 5
                    ? 'bg-triage-yellow'
                    : 'bg-accent-500'
                : 'bg-ink-200/80 dark:bg-ink-700/60'
            )}
          />
        );
      })}
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2 px-4 py-10 text-center">
      <span className="grid h-11 w-11 place-items-center rounded-full bg-ink-100 text-ink-400 dark:bg-ink-700/40 dark:text-ink-300">
        <Activity className="h-5 w-5" aria-hidden />
      </span>
      <p className="text-sm font-medium">Symptom Matrix vuota</p>
      <p className="max-w-[18rem] text-xs text-ink-400">
        Avvia il colloquio: i sintomi vengono estratti automaticamente e organizzati qui in tempo
        reale.
      </p>
    </div>
  );
}

function formatOnset(iso: string): string {
  try {
    const d = new Date(iso);
    return d.toLocaleString('it-IT', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}
