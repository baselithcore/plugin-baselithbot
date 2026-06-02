import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronDown,
  ChevronRight,
  AlertCircle,
  ShieldCheck,
  Stethoscope,
  Clock,
  Sparkles,
  Download,
} from 'lucide-react';
import clsx from 'clsx';
import type { DifferentialHypothesis, LivePreview, TriageReport } from '../lib/types';
import { TRIAGE_LABEL, TRIAGE_SUBTITLE, TRIAGE_TOKENS } from '../lib/triage-tokens';
import { IntakeReportView } from './IntakeReportView';

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

function ReportView({
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

function HypothesisCard({
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

function _slugifyForFilename(value: string | null | undefined): string {
  return (
    (value ?? 'report')
      .replace(/[^a-zA-Z0-9-_]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .toLowerCase()
      .slice(0, 48) || 'report'
  );
}

function _triggerDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function downloadReportMarkdown(report: TriageReport) {
  const stamp = new Date(report.generated_at).toISOString().slice(0, 16).replace(/[:T]/g, '-');
  const filename = `pretriage-${_slugifyForFilename(report.patient_pseudonym)}-${stamp}.md`;
  const md =
    report.intake_report ??
    `# Pre-triage clinico\n\n_(nessun intake report disponibile)_\n\n` +
      `Codice triage: ${report.triage.code}\n` +
      `Razionale: ${report.triage.rationale}\n`;
  _triggerDownload(new Blob([md], { type: 'text/markdown;charset=utf-8' }), filename);
}

function downloadReportJson(report: TriageReport) {
  const stamp = new Date(report.generated_at).toISOString().slice(0, 16).replace(/[:T]/g, '-');
  const filename = `pretriage-${_slugifyForFilename(report.patient_pseudonym)}-${stamp}.json`;
  _triggerDownload(
    new Blob([JSON.stringify(report, null, 2)], { type: 'application/json;charset=utf-8' }),
    filename
  );
}

function formatTimestamp(iso: string): string {
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
