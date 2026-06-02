import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, CheckCircle2, XCircle, PenLine, ShieldCheck } from 'lucide-react';
import type { TriageReport } from '../lib/types';
import { TRIAGE_LABEL, TRIAGE_TOKENS } from '../lib/triage-tokens';
import clsx from 'clsx';

interface Props {
  open: boolean;
  report: TriageReport | null;
  onClose: () => void;
  onSubmit: (input: { approved: boolean; clinicianId: string; notes: string }) => Promise<void>;
  pending: boolean;
}

export function ValidationModal({ open, report, onClose, onSubmit, pending }: Props) {
  const [clinicianId, setClinicianId] = useState('');
  const [notes, setNotes] = useState('');
  const idRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !pending) onClose();
    };
    document.addEventListener('keydown', onKey);
    const t = setTimeout(() => idRef.current?.focus(), 60);
    return () => {
      document.removeEventListener('keydown', onKey);
      clearTimeout(t);
    };
  }, [open, pending, onClose]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.16 }}
          className="fixed inset-0 z-40 flex items-center justify-center bg-ink-900/55 p-4 backdrop-blur"
          role="dialog"
          aria-modal="true"
          aria-labelledby="validation-title"
        >
          <motion.div
            initial={{ opacity: 0, y: 12, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, scale: 0.98 }}
            transition={{ duration: 0.22, ease: [0.16, 1, 0.3, 1] }}
            className="surface-strong relative w-full max-w-3xl overflow-hidden"
          >
            <button
              type="button"
              onClick={onClose}
              className="absolute right-3 top-3 z-10 rounded-lg p-2 text-ink-400 transition hover:bg-ink-100 dark:hover:bg-ink-700/40"
              aria-label="Chiudi"
              disabled={pending}
            >
              <X className="h-4 w-4" aria-hidden />
            </button>
            <div className="grid grid-cols-1 md:grid-cols-[1fr_1.1fr]">
              <ReportPreview report={report} />
              <SignatureForm
                idRef={idRef}
                clinicianId={clinicianId}
                setClinicianId={setClinicianId}
                notes={notes}
                setNotes={setNotes}
                pending={pending}
                onSubmit={onSubmit}
              />
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

function ReportPreview({ report }: { report: TriageReport | null }) {
  if (!report) {
    return (
      <div className="bg-surface-sunken/60 p-6 dark:bg-surface-dark-sunken/40">
        <p className="text-sm text-ink-400">Nessun report disponibile.</p>
      </div>
    );
  }
  const tokens = TRIAGE_TOKENS[report.triage.code];
  return (
    <div className="bg-surface-sunken/60 p-6 dark:bg-surface-dark-sunken/40">
      <div className="section-title">Anteprima report</div>
      <div className="mt-3 flex items-center gap-3">
        <span
          className={clsx(
            'grid h-12 w-12 place-items-center rounded-xl font-display text-sm font-bold tracking-tight',
            tokens.chip
          )}
          aria-hidden
        >
          {report.triage.code}
        </span>
        <div>
          <div className="font-display text-base font-semibold tracking-tight">
            {TRIAGE_LABEL[report.triage.code]}
          </div>
          <div className="text-2xs uppercase tracking-[0.12em] text-ink-400">
            {report.patient_pseudonym}
          </div>
        </div>
      </div>
      <p className="mt-4 text-sm leading-relaxed text-ink-700 dark:text-ink-100">
        {report.triage.rationale}
      </p>
      <div className="mt-4">
        <div className="section-title mb-1.5">Prima ipotesi</div>
        {report.differential.hypotheses[0] ? (
          <div className="rounded-lg border border-ink-200/70 bg-white p-3 dark:border-ink-700/60 dark:bg-surface-dark-raised">
            <div className="flex items-center justify-between">
              <span className="text-sm font-semibold">
                {report.differential.hypotheses[0].condition}
              </span>
              <span className="num font-mono text-xs font-semibold text-accent-700 dark:text-accent-300">
                {Math.round(report.differential.hypotheses[0].confidence * 100)}%
              </span>
            </div>
            {report.differential.hypotheses[0].icd10 && (
              <span className="pill-mono mt-1.5">
                ICD {report.differential.hypotheses[0].icd10}
              </span>
            )}
          </div>
        ) : (
          <p className="text-xs text-ink-400">Nessuna ipotesi disponibile.</p>
        )}
      </div>
      <p className="mt-6 border-t border-ink-200/70 pt-3 text-2xs leading-relaxed text-ink-500 dark:border-ink-700/60 dark:text-ink-300">
        {report.disclaimer}
      </p>
    </div>
  );
}

function SignatureForm({
  idRef,
  clinicianId,
  setClinicianId,
  notes,
  setNotes,
  pending,
  onSubmit,
}: {
  idRef: React.MutableRefObject<HTMLInputElement | null>;
  clinicianId: string;
  setClinicianId: (v: string) => void;
  notes: string;
  setNotes: (v: string) => void;
  pending: boolean;
  onSubmit: Props['onSubmit'];
}) {
  return (
    <div className="p-6">
      <div className="flex items-center gap-2">
        <span className="grid h-9 w-9 place-items-center rounded-lg bg-accent-50 text-accent-700 ring-1 ring-accent-200/80 dark:bg-accent-800/30 dark:text-accent-200 dark:ring-accent-700/60">
          <ShieldCheck className="h-4 w-4" aria-hidden />
        </span>
        <div>
          <h3 id="validation-title" className="font-display text-lg font-semibold tracking-tight">
            Validazione clinica
          </h3>
          <p className="text-xs text-ink-400">Firma immutabile · timestamp registrato</p>
        </div>
      </div>

      <div className="mt-5 space-y-3.5">
        <div>
          <label htmlFor="clinician_id" className="section-title mb-1 block">
            ID medico
          </label>
          <div className="relative">
            <PenLine
              className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-ink-400"
              aria-hidden
            />
            <input
              ref={idRef}
              id="clinician_id"
              type="text"
              value={clinicianId}
              onChange={(e) => setClinicianId(e.target.value)}
              className="input pl-9"
              placeholder="es. dr.rossi@ospedale.it"
              disabled={pending}
              autoComplete="off"
            />
          </div>
        </div>
        <div>
          <label htmlFor="notes" className="section-title mb-1 block">
            Note (opzionali)
          </label>
          <textarea
            id="notes"
            rows={3}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            className="input resize-none"
            placeholder="Considerazioni cliniche, modifiche al codice, ecc."
            disabled={pending}
          />
        </div>
      </div>

      <div className="mt-6 flex flex-col-reverse gap-2 sm:flex-row sm:justify-end">
        <button
          type="button"
          onClick={() => void onSubmit({ approved: false, clinicianId, notes })}
          disabled={pending || !clinicianId.trim()}
          className="btn-danger-ghost"
        >
          <XCircle className="h-4 w-4" aria-hidden />
          Rifiuta
        </button>
        <button
          type="button"
          onClick={() => void onSubmit({ approved: true, clinicianId, notes })}
          disabled={pending || !clinicianId.trim()}
          className="btn-primary"
        >
          <CheckCircle2 className="h-4 w-4" aria-hidden />
          Approva
        </button>
      </div>
      <p className="mt-4 flex items-center gap-1.5 text-2xs text-ink-400">
        <span className="kbd">Esc</span>
        per chiudere senza firmare
      </p>
    </div>
  );
}
