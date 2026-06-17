import { motion } from 'framer-motion';
import { AlertCircle, ShieldCheck, Sparkles, Stethoscope } from 'lucide-react';
import clsx from 'clsx';
import type { LivePreview, TriageReport } from '../../lib/types';
import { TRIAGE_LABEL, TRIAGE_SUBTITLE, TRIAGE_TOKENS } from '../../lib/triage-tokens';
import { IntakeReportView } from '../IntakeReportView';
import { HypothesisCard } from './HypothesisCard';
import { ReportView } from './ReportView';

interface Props {
  report: TriageReport | null;
  preview: LivePreview | null;
  pending: boolean;
  onOpenValidation: () => void;
}

export function TriagePanel({ report, preview, pending, onOpenValidation }: Props) {
  const showPreview = !report && preview;
  return (
    <section className="surface flex h-full flex-col overflow-hidden" aria-label="Triage report">
      <header className="flex items-center justify-between border-b border-ink-200/70 px-5 py-3.5 dark:border-ink-700/60">
        <div className="flex items-center gap-2.5">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-ink-100/80 text-ink-600 dark:bg-ink-700/40 dark:text-ink-200">
            <Stethoscope className="h-4 w-4" aria-hidden />
          </span>
          <div className="leading-tight">
            <h2 className="font-display text-sm font-semibold tracking-tight">
              Differential & Triage
            </h2>
            <p className="text-2xs uppercase tracking-[0.14em] text-ink-400">
              {showPreview ? 'Anteprima · live' : 'Deduttivo · agente'}
            </p>
          </div>
        </div>
        <span className="pill-accent">
          <ShieldCheck className="h-3 w-3" aria-hidden />
          HITL
        </span>
      </header>

      <div className="scroll-fade flex-1 overflow-y-auto px-4 py-4">
        {!report && !preview && !pending && <Empty />}
        {pending && !report && <Skeleton />}
        {showPreview && <PreviewView preview={preview!} />}
        {report && <ReportView report={report} onOpenValidation={onOpenValidation} />}
      </div>
    </section>
  );
}

function PreviewView({ preview }: { preview: LivePreview }) {
  const code = preview.triage.code;
  const tokens = TRIAGE_TOKENS[code];
  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 rounded-lg border border-accent-200/80 bg-accent-50/60 px-3 py-2 text-xs text-accent-700 dark:border-accent-700/60 dark:bg-accent-800/30 dark:text-accent-200">
        <Sparkles className="h-3.5 w-3.5" aria-hidden />
        <span>
          Anteprima live · aggiornata ad ogni turno. Per il report definitivo firmato dal medico,
          premi <span className="kbd">Report</span>.
        </span>
      </div>

      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.24, ease: [0.16, 1, 0.3, 1] }}
        className={clsx(
          'relative overflow-hidden rounded-2xl border bg-white shadow-e1 dark:bg-surface-dark-raised',
          tokens.border
        )}
      >
        <div className={clsx('h-1.5 w-full', tokens.bar)} aria-hidden />
        <div className="p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <div
                className={clsx(
                  'text-2xs font-semibold uppercase tracking-[0.14em]',
                  tokens.textOnSurface
                )}
              >
                {TRIAGE_SUBTITLE[code]}
              </div>
              <div className="mt-1 font-display text-display font-semibold tracking-tight">
                {TRIAGE_LABEL[code]}
              </div>
            </div>
            <span
              className={clsx(
                'grid h-12 w-12 shrink-0 place-items-center rounded-xl font-display text-xs font-bold tracking-tight shadow-e1',
                tokens.chip
              )}
              aria-hidden
            >
              {code}
            </span>
          </div>
          <p className="mt-3 text-xs leading-relaxed text-ink-700 dark:text-ink-100">
            {preview.triage.rationale}
          </p>
          <div className="mt-3 flex flex-wrap items-center gap-2 text-2xs text-ink-500 dark:text-ink-300">
            <span className="pill-mono num">{preview.symptom_count} sintomi</span>
            {preview.red_flag_count > 0 && (
              <span className="pill border-triage-red/40 bg-triage-red-soft text-triage-red">
                <AlertCircle className="h-3 w-3" aria-hidden />
                {preview.red_flag_count} red flag
              </span>
            )}
          </div>
        </div>
      </motion.div>

      <section aria-label="Differential Diagnosis preview">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="section-title">DDx in costruzione</h3>
          <span className="pill-mono num">{preview.differential.hypotheses.length} ipotesi</span>
        </div>
        {preview.differential.hypotheses.length === 0 ? (
          <p className="rounded-lg border border-ink-200/70 bg-white/60 px-3 py-2.5 text-xs text-ink-400 dark:border-ink-700/60 dark:bg-surface-dark-raised/60">
            Raccolgo ancora sintomi per formulare la diagnosi differenziale.
          </p>
        ) : (
          <ol className="space-y-2" role="list">
            {preview.differential.hypotheses.slice(0, 5).map((h, i) => (
              <HypothesisCard key={`${h.condition}-${i}`} hypothesis={h} rank={i + 1} />
            ))}
          </ol>
        )}
        <p className="mt-2 text-2xs italic text-ink-400">
          {preview.differential.notes ?? 'Ranking provvisorio.'}
        </p>
      </section>

      {preview.intake_report && <IntakeReportView markdown={preview.intake_report} />}
    </div>
  );
}

function Empty() {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-2 px-6 py-12 text-center">
      <span className="grid h-12 w-12 place-items-center rounded-full bg-ink-100 text-ink-400 dark:bg-ink-700/40 dark:text-ink-300">
        <Sparkles className="h-5 w-5" aria-hidden />
      </span>
      <p className="text-sm font-medium">Report non ancora generato</p>
      <p className="max-w-[20rem] text-xs leading-relaxed text-ink-400">
        Completa il colloquio o premi <span className="kbd">Report</span> per produrre il pre-triage
        strutturato pronto per la validazione del medico.
      </p>
    </div>
  );
}

function Skeleton() {
  return (
    <div className="space-y-3" aria-hidden>
      <div className="h-28 animate-pulse rounded-2xl bg-ink-100 dark:bg-ink-700/40" />
      <div className="h-12 animate-pulse rounded-xl bg-ink-100 dark:bg-ink-700/40" />
      <div className="h-12 animate-pulse rounded-xl bg-ink-100 dark:bg-ink-700/40" />
      <div className="h-12 animate-pulse rounded-xl bg-ink-100 dark:bg-ink-700/40" />
    </div>
  );
}
