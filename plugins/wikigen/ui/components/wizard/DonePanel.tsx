import { AlertCircle, CheckCircle2, Sparkles } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import {
  activateNow,
  fetchJobs,
  pollBackendUp,
  probeBackend,
  restartBackend,
  StaleBootIdError,
  type ScaffoldResultResponse,
} from '../../lib/api';
import { Button, Callout } from '../ui';
import { Row } from './atoms';
import { shorten } from './helpers';
import { PipelinePanel } from './PipelinePanel';
import type { DoneState, IngestSnapshot } from './pipeline-types';

export type { DoneState, IngestSnapshot } from './pipeline-types';

export function DonePanel({
  result,
  expectedDocs,
  onClose,
}: {
  result: ScaffoldResultResponse;
  expectedDocs: number;
  onClose: () => void;
}) {
  const cmd = `APP_DOMAIN=${result.name} python -m llm_wiki serve --reload`;
  const [copied, setCopied] = useState(false);
  // `auto-running` covers the auto-restart that fires immediately after
  // scaffold success — UI shows progress without requiring user action.
  const [doneState, setDoneState] = useState<DoneState>('sending');
  const [ingest, setIngest] = useState<IngestSnapshot>({
    total: expectedDocs,
    done: 0,
    running: 0,
    errors: 0,
    files: [],
  });
  const autoStartedRef = useRef(false);

  // Persist synthesis warning so it survives the post-restart wizard unmount
  // and surfaces once on first app load (App.tsx reads `pending_synth_warning`).
  useEffect(() => {
    if (result.synthesis_warning && !result.synthesis_applied) {
      try {
        window.localStorage.setItem(
          'onboarding.pending_synth_warning',
          JSON.stringify({ pack: result.name, msg: result.synthesis_warning })
        );
      } catch {
        /* ignore */
      }
    }
  }, [result.name, result.synthesis_applied, result.synthesis_warning]);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(cmd);
      setCopied(true);
      toast.success('Comando copiato');
      setTimeout(() => setCopied(false), 1500);
    } catch {
      toast.error('Clipboard non disponibile');
    }
  };

  const pollIngestUntilDone = async () => {
    const startedAt = Date.now();
    const maxMs = 30 * 60_000; // 30 min hard cap; pipeline is heavy.
    let stableEmptyChecks = 0;
    while (Date.now() - startedAt < maxMs) {
      let jobs: Awaited<ReturnType<typeof fetchJobs>>['jobs'] = [];
      try {
        const r = await fetchJobs(50);
        jobs = r.jobs;
      } catch {
        await new Promise((res) => setTimeout(res, 2000));
        continue;
      }
      // Aggregate per-filename (worker may emit multiple events).
      const byName = new Map<string, IngestSnapshot['files'][number]>();
      let runningCount = 0;
      let doneCount = 0;
      let errorCount = 0;
      for (const j of jobs) {
        const prev = byName.get(j.filename);
        // prefer the most-advanced status if same filename appears twice
        const advance = (s: typeof j.status) =>
          (({ queued: 0, running: 1, done: 2, error: 2 }) as const)[s];
        if (!prev || advance(j.status) >= advance(prev.status)) {
          byName.set(j.filename, {
            filename: j.filename,
            status: j.status,
            pages_written: j.pages_written ?? 0,
            summary: j.summary ?? '',
          });
        }
      }
      for (const f of byName.values()) {
        if (f.status === 'running' || f.status === 'queued') runningCount++;
        else if (f.status === 'done') doneCount++;
        else if (f.status === 'error') errorCount++;
      }
      const total = Math.max(byName.size, expectedDocs);
      setIngest({
        total,
        done: doneCount,
        running: runningCount,
        errors: errorCount,
        files: Array.from(byName.values()).sort((a, b) => a.filename.localeCompare(b.filename)),
      });

      // Done condition: no running/queued jobs AND we've observed all
      // expected docs (or expected was 0 from the start).
      const allSettled = runningCount === 0;
      const allObserved = expectedDocs === 0 || byName.size >= expectedDocs;
      if (allSettled && allObserved) {
        // require two consecutive empty checks to avoid flicker before
        // the registry rehydrates from disk after restart.
        stableEmptyChecks++;
        if (stableEmptyChecks >= 2) return;
      } else {
        stableEmptyChecks = 0;
      }
      await new Promise((res) => setTimeout(res, 2000));
    }
    // timeout: don't fail the wizard, just stop polling.
  };

  const triggerRestart = async () => {
    setDoneState('sending');
    try {
      // Capture pre-restart boot_id so pollBackendUp can wait for the
      // worker to ACTUALLY restart. Without this, /branding may report
      // ready immediately because scaffold mutated `os.environ` in the
      // still-running old worker — wizard would then poll for ingest
      // jobs against an empty registry and never see uploaded docs.
      let bootIdBefore: string | undefined;
      try {
        const probe = await probeBackend();
        bootIdBefore = probe.boot_id;
      } catch {
        /* old build without boot_id; fallback to plain ready check */
      }
      const restart = await restartBackend(500);
      if (restart.requires_manual) {
        // Bare mode: cannot restart, but we can replay the lifespan
        // side-effects in-process so the wizard finishes without
        // forcing the user to a terminal. Scaffold already mutated
        // os.environ + reset_pack_cache; activate-now wires up the
        // qdrant collection / embedder warmup / autostart ingest that
        // normally only fire at boot.
        setDoneState('waiting');
        try {
          const act = await activateNow();
          if (!act.ok || act.setup_mode) {
            setDoneState('manual_required');
            toast.error(
              act.note || 'Attivazione in-process non riuscita: avvia il server con --reload.'
            );
            return;
          }
        } catch (err) {
          setDoneState('manual_required');
          toast.error(
            err instanceof Error
              ? `Attivazione in-process fallita: ${err.message}`
              : 'Attivazione in-process fallita.'
          );
          return;
        }
        if (expectedDocs > 0) {
          setDoneState('ingesting');
          await pollIngestUntilDone();
        }
        setDoneState('all_done');
        return;
      }
      setDoneState('waiting');
      await pollBackendUp(120_000, 1500, bootIdBefore);
      // expectedDocs > 0 → poll ingest. else jump straight to all_done.
      if (expectedDocs > 0) {
        setDoneState('ingesting');
        await pollIngestUntilDone();
      }
      setDoneState('all_done');
    } catch (err) {
      if (err instanceof StaleBootIdError) {
        setDoneState('manual_required');
        toast.error(
          'Il processo non si è riavviato (boot_id invariato). Esegui il comando manualmente.'
        );
        return;
      }
      setDoneState('error');
      toast.error(
        'Riavvio non riuscito automaticamente. Lancia il comando manualmente o verifica il process supervisor.'
      );
    }
  };

  // Auto-fire the restart + ingestion flow as soon as the panel mounts.
  // The user already committed by clicking "Crea wiki" in the previous
  // step — no extra confirmation here. They see the progress bar
  // straight away and only land on the chat once ingestion is done.
  useEffect(() => {
    if (autoStartedRef.current) return;
    autoStartedRef.current = true;
    void triggerRestart();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const openWiki = () => {
    // Hard reload so the entire app re-hydrates with the new tenant.
    window.location.reload();
  };

  const progressPct =
    ingest.total > 0
      ? Math.min(100, Math.round(((ingest.done + ingest.errors) / ingest.total) * 100))
      : 100;

  return (
    <div className="space-y-4 px-5 py-6">
      <Callout tone="success" icon={CheckCircle2} title={`Wiki «${result.name}» creata`}>
        <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-[11px] font-mono text-ink">
          <Row k="cartella pack" v={shorten(result.target_pack_dir)} />
          <Row k="vault" v={shorten(result.vault_path)} />
          <Row k="configurazione" v={result.env_written ? 'salvata' : 'non scritta'} />
          <Row k="attiva" v={result.activated ? 'sì' : 'no'} />
          {result.synthesis_applied && (
            <Row
              k="prompt"
              v={`personalizzato${result.synthesis_model ? ` · ${result.synthesis_model}` : ''}`}
            />
          )}
          {expectedDocs > 0 && <Row k="documenti" v={`${expectedDocs} PDF da elaborare`} />}
        </dl>
        {result.synthesis_warning && !result.synthesis_applied && (
          <div className="mt-2 flex items-start gap-1.5 text-[10.5px] text-[var(--color-warning)]">
            <AlertCircle size={11} className="mt-0.5 shrink-0" aria-hidden />
            <span>
              Personalizzazione del prompt non eseguita ({result.synthesis_warning}). Sono stati
              usati i prompt generici di <code>_template</code> — modificali in{' '}
              <code>domains/{result.name}/prompts/system.j2</code>.
            </span>
          </div>
        )}
      </Callout>

      {/* Auto-running pipeline status — single panel that morphs through
          phases (restart → backend up → ingestion → done). User stays
          here until everything is ready. */}
      <PipelinePanel
        state={doneState}
        expectedDocs={expectedDocs}
        ingest={ingest}
        pct={progressPct}
        cmd={cmd}
        copied={copied}
        onCopy={copy}
        onRetry={triggerRestart}
      />

      <div className="flex items-center justify-end gap-2 border-t border-[var(--color-border)] pt-3">
        {doneState === 'all_done' ? (
          <Button leadingIcon={Sparkles} onClick={openWiki} autoFocus>
            Apri la wiki
          </Button>
        ) : doneState === 'error' || doneState === 'manual_required' ? (
          <Button variant="secondary" onClick={onClose}>
            Chiudi
          </Button>
        ) : (
          <span className="text-[10.5px] text-ink-subtle">
            Attendi il completamento prima di chiudere.
          </span>
        )}
      </div>
    </div>
  );
}
