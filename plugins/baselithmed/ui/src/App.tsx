import { useCallback, useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import { AlertOctagon } from 'lucide-react';
import { TopBar } from './components/TopBar';
import { ChatPanel } from './components/ChatPanel';
import { SymptomMatrixPanel } from './components/SymptomMatrixPanel';
import { TriagePanel } from './components/TriagePanel';
import { ValidationModal } from './components/ValidationModal';
import { StatusFooter } from './components/StatusFooter';
import {
  createSession,
  fetchInfo,
  finalizeTriage,
  postInterviewTurn,
  validateReport,
  type BackendInfo,
} from './lib/api';
import type { ChatMessage, LivePreview, Symptom, TriageReport } from './lib/types';

const SEED_MESSAGE: ChatMessage = {
  id: 'seed',
  role: 'agent',
  text:
    "Buongiorno, sono l'assistente clinico. Le farò alcune domande con calma per " +
    'preparare un riassunto destinato al medico. Mi può dire come si sente in questo momento?',
  meta: { tone: 'empathic', target_slot: 'chief_complaint' },
  timestamp: new Date().toISOString(),
};

export default function App() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [pseudonym, setPseudonym] = useState<string | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([SEED_MESSAGE]);
  const [symptoms, setSymptoms] = useState<Symptom[]>([]);
  const [deniedSymptoms, setDeniedSymptoms] = useState<string[]>([]);
  const [progress, setProgress] = useState(0);
  const [pending, setPending] = useState(false);
  const [report, setReport] = useState<TriageReport | null>(null);
  const [preview, setPreview] = useState<LivePreview | null>(null);
  const [reportPending, setReportPending] = useState(false);
  const [validationOpen, setValidationOpen] = useState(false);
  const [validating, setValidating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [online, setOnline] = useState(typeof navigator !== 'undefined' ? navigator.onLine : true);
  const [info, setInfo] = useState<BackendInfo | null>(null);

  useEffect(() => {
    const setOn = () => setOnline(true);
    const setOff = () => setOnline(false);
    window.addEventListener('online', setOn);
    window.addEventListener('offline', setOff);
    return () => {
      window.removeEventListener('online', setOn);
      window.removeEventListener('offline', setOff);
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    const delays = [400, 800, 1600, 3200, 6400];
    (async () => {
      let lastErr: unknown = null;
      for (let attempt = 0; attempt <= delays.length; attempt++) {
        if (cancelled) return;
        try {
          const [s, i] = await Promise.all([createSession(), fetchInfo()]);
          if (cancelled) return;
          setSessionId(s.session_id);
          setPseudonym(s.patient_pseudonym);
          setInfo(i);
          setError(null);
          return;
        } catch (e) {
          lastErr = e;
          if (attempt < delays.length) {
            await new Promise((r) => setTimeout(r, delays[attempt]));
          }
        }
      }
      if (cancelled) return;
      setError(lastErr instanceof Error ? lastErr.message : 'Impossibile aprire la sessione.');
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const turns = useMemo(() => messages.filter((m) => m.role === 'patient').length, [messages]);
  const canFinalize = useMemo(() => symptoms.length > 0, [symptoms]);

  const handleSend = useCallback(
    async (text: string) => {
      if (!sessionId) return;
      const patientMsg: ChatMessage = {
        id: crypto.randomUUID(),
        role: 'patient',
        text,
        timestamp: new Date().toISOString(),
      };
      setMessages((m) => [...m, patientMsg]);
      setPending(true);
      setError(null);
      try {
        const res = await postInterviewTurn(sessionId, text);
        const data = res.data;
        if (data.escalate) {
          setMessages((m) => [
            ...m,
            {
              id: crypto.randomUUID(),
              role: 'agent',
              text: data.instruction ?? 'È necessario un intervento medico immediato.',
              meta: { escalate: true },
              timestamp: new Date().toISOString(),
            },
          ]);
        } else if (data.question) {
          setMessages((m) => [
            ...m,
            {
              id: crypto.randomUUID(),
              role: 'agent',
              text: data.question!,
              meta: {
                tone: data.tone,
                target_slot: data.target_slot,
                rationale: data.rationale,
              },
              timestamp: new Date().toISOString(),
            },
          ]);
        }
        if (typeof data.progress === 'number') setProgress(data.progress);
        if (data.matrix && Array.isArray(data.matrix.symptoms)) {
          setSymptoms(data.matrix.symptoms);
        } else if (Array.isArray(data.known_symptoms)) {
          setSymptoms((prev) => mergeSymptomNames(prev, data.known_symptoms!));
        }
        if (data.matrix && Array.isArray(data.matrix.denied_symptoms)) {
          setDeniedSymptoms(data.matrix.denied_symptoms);
        }
        // Auto-finalize: the backend ships a full TriageReport (not the
        // is_preview-shaped LivePreview). Promote it straight to `report`
        // so the UI transitions from "anteprima live" to the validation
        // panel without a second round-trip.
        const autoFinalized = (data as { auto_finalized?: boolean }).auto_finalized;
        if (autoFinalized && data.preview) {
          setReport(data.preview as unknown as TriageReport);
          setPreview(null);
        } else if (data.preview) {
          setPreview(data.preview);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Errore di rete.');
      } finally {
        setPending(false);
      }
    },
    [sessionId]
  );

  const handleFinalize = useCallback(async () => {
    if (!sessionId) return;
    setReportPending(true);
    setError(null);
    try {
      const res = await finalizeTriage(sessionId, pseudonym ?? undefined);
      setReport(res.data);
      setSymptoms(res.data.symptom_matrix.symptoms);
      if (Array.isArray(res.data.symptom_matrix.denied_symptoms)) {
        setDeniedSymptoms(res.data.symptom_matrix.denied_symptoms);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Errore generazione report.');
    } finally {
      setReportPending(false);
    }
  }, [sessionId, pseudonym]);

  const submitValidation = useCallback(
    async (input: { approved: boolean; clinicianId: string; notes: string }) => {
      if (!sessionId || !report) return;
      setValidating(true);
      setError(null);
      try {
        await validateReport(sessionId, input.approved, input.clinicianId, input.notes);
        setReport((r) =>
          r
            ? {
                ...r,
                status: input.approved ? 'VALIDATED' : 'REJECTED',
                validator_signature: input.clinicianId,
              }
            : r
        );
        setValidationOpen(false);
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Errore validazione.');
      } finally {
        setValidating(false);
      }
    },
    [sessionId, report]
  );

  return (
    <div className="flex h-full flex-col">
      <TopBar pseudonym={pseudonym} sessionId={sessionId} turns={turns} online={online} />
      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}
      <main className="mx-auto flex w-full max-w-[1480px] flex-1 gap-5 px-5 pb-5 pt-5 md:px-7 md:pb-7">
        <motion.section layout className="min-h-0 flex-1 [grid-area:chat]" aria-label="Colloquio">
          <ChatPanel
            messages={messages}
            pending={pending}
            progress={progress}
            onSend={handleSend}
            onFinalize={handleFinalize}
            canFinalize={canFinalize}
          />
        </motion.section>
        <motion.aside layout className="hidden min-h-0 w-[400px] shrink-0 flex-col gap-5 lg:flex">
          <div className="flex-[1.05] min-h-0">
            <SymptomMatrixPanel symptoms={symptoms} deniedSymptoms={deniedSymptoms} />
          </div>
          <div className="flex-[1.6] min-h-0">
            <TriagePanel
              report={report}
              preview={preview}
              pending={reportPending}
              onOpenValidation={() => setValidationOpen(true)}
            />
          </div>
        </motion.aside>
      </main>
      <StatusFooter
        modelId={info?.model_id ?? undefined}
        validatorId={report?.validator_signature ?? null}
      />
      <ValidationModal
        open={validationOpen}
        report={report}
        onClose={() => setValidationOpen(false)}
        onSubmit={submitValidation}
        pending={validating}
      />
    </div>
  );
}

function ErrorBanner({ message, onDismiss }: { message: string; onDismiss: () => void }) {
  return (
    <div
      role="alert"
      className="mx-auto mt-3 flex w-full max-w-[1480px] items-center justify-between gap-3 rounded-xl border border-triage-red/40 bg-triage-red-soft/60 px-4 py-2.5 text-sm text-triage-red-ink dark:bg-triage-red-soft/15 dark:text-triage-red"
    >
      <span className="flex items-center gap-2">
        <AlertOctagon className="h-4 w-4" aria-hidden />
        {message}
      </span>
      <button
        type="button"
        onClick={onDismiss}
        className="text-2xs font-semibold uppercase tracking-[0.12em] underline-offset-4 hover:underline"
      >
        Chiudi
      </button>
    </div>
  );
}

function mergeSymptomNames(prev: Symptom[], names: string[]): Symptom[] {
  const known = new Set(prev.map((s) => s.canonical_name));
  const additions: Symptom[] = [];
  for (const name of names) {
    if (!known.has(name)) {
      additions.push({
        canonical_name: name,
        raw_quote: '',
        body_site: null,
        onset: null,
        severity_nrs: null,
        character: [],
        icd10_hint: null,
        source_turn_id: '',
      });
      known.add(name);
    }
  }
  return additions.length ? [...prev, ...additions] : prev;
}
