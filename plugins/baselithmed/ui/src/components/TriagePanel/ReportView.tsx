import { motion } from 'framer-motion';
import { AlertCircle, Clock, Download, ShieldCheck, Sparkles } from 'lucide-react';
import clsx from 'clsx';
import type { TriageReport } from '../../lib/types';
import { TRIAGE_LABEL, TRIAGE_SUBTITLE, TRIAGE_TOKENS } from '../../lib/triage-tokens';
import { IntakeReportView } from '../IntakeReportView';
import { HypothesisCard } from './HypothesisCard';
import { downloadReportJson, downloadReportMarkdown, formatTimestamp } from './download';

export function ReportView({
  report,
  onOpenValidation,
}: {
  report: TriageReport;
  onOpenValidation: () => void;
}) {
  const code = report.triage.code;
  const tokens = TRIAGE_TOKENS[code];
  const isRed = code === 'RED';

  return (
    <div className="space-y-5">
      <motion.div
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.28, ease: [0.16, 1, 0.3, 1] }}
        className={clsx(
          'relative overflow-hidden rounded-2xl border bg-white shadow-e2 dark:bg-surface-dark-raised',
          tokens.border
        )}
        role="status"
        aria-live="polite"
      >
        <div className={clsx('h-1.5 w-full', tokens.bar)} aria-hidden />
        <div className="p-5">
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
              <div className="mt-1 font-display text-hero font-semibold tracking-tight">
                {TRIAGE_LABEL[code]}
              </div>
            </div>
            <CodeBadge code={code} />
          </div>
          <div className="mt-4 grid grid-cols-2 gap-3">
            <Metric
              icon={<Clock className="h-3.5 w-3.5" aria-hidden />}
              label="Tempo target"
              value={
                report.triage.target_latency_minutes === 0
                  ? 'Immediato'
                  : `≤ ${report.triage.target_latency_minutes} min`
              }
              highlight={isRed}
            />
            <Metric
              icon={<Sparkles className="h-3.5 w-3.5" aria-hidden />}
              label="Modello"
              value={report.differential.model_id}
              mono
            />
          </div>
          <p className="mt-4 border-t border-ink-200/70 pt-3 text-sm leading-relaxed text-ink-700 dark:border-ink-700/60 dark:text-ink-100">
            {report.triage.rationale}
          </p>
          {report.triage.red_flag_overrides.length > 0 && (
            <ul className="mt-3 space-y-1.5 rounded-lg bg-triage-red-soft/50 p-3 text-xs text-triage-red dark:bg-triage-red-soft/15">
              {report.triage.red_flag_overrides.map((rf) => (
                <li key={rf} className="flex items-start gap-1.5">
                  <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
                  <span>{rf}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </motion.div>

      <section aria-label="Differential Diagnosis">
        <div className="mb-2 flex items-center justify-between">
          <h3 className="section-title">Differential Diagnosis</h3>
          <span className="pill-mono num">{report.differential.hypotheses.length} ipotesi</span>
        </div>
        <ol className="space-y-2" role="list">
          {report.differential.hypotheses.map((h, i) => (
            <HypothesisCard key={`${h.condition}-${i}`} hypothesis={h} rank={i + 1} />
          ))}
        </ol>
      </section>

      {report.intake_report && <IntakeReportView markdown={report.intake_report} />}

      <section
        aria-label="Disclaimer"
        className="rounded-xl border border-ink-200/70 bg-surface-sunken/60 p-3 text-xs leading-relaxed text-ink-500 dark:border-ink-700/60 dark:bg-surface-dark-sunken/40 dark:text-ink-200"
      >
        <div className="font-semibold text-ink-800 dark:text-ink-50">Disclaimer</div>
        <p className="mt-1">{report.disclaimer}</p>
      </section>

      <AuditFooter report={report} onOpenValidation={onOpenValidation} />
    </div>
  );
}

function CodeBadge({ code }: { code: TriageReport['triage']['code'] }) {
  const tokens = TRIAGE_TOKENS[code];
  const isRed = code === 'RED';
  return (
    <span
      className={clsx(
        'grid h-14 w-14 shrink-0 place-items-center rounded-2xl font-display text-base font-bold tracking-tight shadow-e1',
        tokens.chip,
        isRed && 'animate-pulse-red'
      )}
      aria-hidden
    >
      {code}
    </span>
  );
}

function Metric({
  icon,
  label,
  value,
  highlight,
  mono,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  highlight?: boolean;
  mono?: boolean;
}) {
  return (
    <div className="rounded-lg border border-ink-200/70 bg-surface-sunken/50 px-3 py-2.5 dark:border-ink-700/60 dark:bg-surface-dark-sunken/40">
      <div className="flex items-center gap-1.5 text-2xs font-medium uppercase tracking-[0.12em] text-ink-400">
        {icon}
        {label}
      </div>
      <div
        className={clsx(
          'mt-1 text-sm font-semibold',
          mono && 'font-mono text-xs',
          highlight && 'text-triage-red'
        )}
      >
        {value}
      </div>
    </div>
  );
}

function AuditFooter({
  report,
  onOpenValidation,
}: {
  report: TriageReport;
  onOpenValidation: () => void;
}) {
  const isPending = report.status === 'PENDING_VALIDATION';
  const isValidated = report.status === 'VALIDATED';
  const isRejected = report.status === 'REJECTED';
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-ink-200/70 bg-white/70 px-4 py-3 dark:border-ink-700/60 dark:bg-surface-dark-raised/60">
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <span
            className={clsx(
              'h-2 w-2 rounded-full',
              isPending && 'animate-pulse bg-triage-yellow',
              isValidated && 'bg-triage-green',
              isRejected && 'bg-triage-red'
            )}
            aria-hidden
          />
          <span className="text-2xs font-semibold uppercase tracking-[0.12em] text-ink-400">
            Stato
          </span>
          <span className="font-mono text-xs font-medium">{report.status}</span>
        </div>
        <div className="flex items-center gap-1.5 text-2xs text-ink-400">
          <Clock className="h-3 w-3" aria-hidden />
          <span className="num">{formatTimestamp(report.generated_at)}</span>
        </div>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => downloadReportMarkdown(report)}
          className="inline-flex items-center gap-1.5 rounded-lg border border-ink-200/80 bg-white/80 px-3 py-2 text-xs font-medium text-ink-700 shadow-e1 transition hover:bg-white dark:border-ink-700/70 dark:bg-surface-dark-raised dark:text-ink-100 dark:hover:bg-surface-dark-sunken"
          aria-label="Scarica report Markdown"
        >
          <Download className="h-3.5 w-3.5" aria-hidden />
          Markdown
        </button>
        <button
          type="button"
          onClick={() => downloadReportJson(report)}
          className="inline-flex items-center gap-1.5 rounded-lg border border-ink-200/80 bg-white/80 px-3 py-2 text-xs font-medium text-ink-700 shadow-e1 transition hover:bg-white dark:border-ink-700/70 dark:bg-surface-dark-raised dark:text-ink-100 dark:hover:bg-surface-dark-sunken"
          aria-label="Scarica report JSON"
        >
          <Download className="h-3.5 w-3.5" aria-hidden />
          JSON
        </button>
        {isPending && (
          <button type="button" onClick={onOpenValidation} className="btn-primary">
            <ShieldCheck className="h-4 w-4" aria-hidden />
            Valida come medico
          </button>
        )}
      </div>
    </div>
  );
}
