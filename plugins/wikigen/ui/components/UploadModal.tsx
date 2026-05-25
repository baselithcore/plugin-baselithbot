import { Loader2, RefreshCw, Upload as UploadIcon } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { toast } from 'sonner';
import {
  fetchJobs,
  fetchRawFiles,
  retryIngestJob,
  runWithConcurrency,
  streamIngestJob,
  uploadRaw,
  type UploadRawOptions,
} from '../lib/api';
import type { IngestJob, IngestStreamEvent, RawFileMeta } from '../lib/types';
import type { DocUploadState } from './upload/DocUploadList';
import { TabButton } from './upload/atoms';
import { ACCEPTED, MAX_MB } from './upload/constants';
import { HistoryTab } from './upload/HistoryTab';
import { UploadTab } from './upload/UploadTab';
import { IconButton, ModalShell } from './ui';

interface Props {
  open: boolean;
  onClose: () => void;
  onIngestComplete?: () => void;
}

type Tab = 'upload' | 'history';

const UPLOAD_CONCURRENCY = 3;

export function UploadModal({ open, onClose, onIngestComplete }: Props) {
  const [tab, setTab] = useState<Tab>('upload');
  const [options, setOptions] = useState<UploadRawOptions>({
    overwrite: false,
    reindex: true,
    dry_run: false,
    only_source_page: false,
    replace_existing: false,
  });
  const [files, setFiles] = useState<File[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [activeJob, setActiveJob] = useState<IngestJob | null>(null);
  const [events, setEvents] = useState<IngestStreamEvent[]>([]);
  const [jobs, setJobs] = useState<IngestJob[]>([]);
  const [rawFiles, setRawFiles] = useState<RawFileMeta[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [docs, setDocs] = useState<DocUploadState[]>([]);
  const inputRef = useRef<HTMLInputElement | null>(null);
  const streamAbort = useRef<AbortController | null>(null);
  const uploadAbort = useRef<AbortController | null>(null);

  const refresh = useCallback(async () => {
    try {
      const [j, f] = await Promise.all([fetchJobs(20), fetchRawFiles()]);
      setJobs(j.jobs);
      setRawFiles(f.files);
    } catch (err) {
      console.warn('refresh jobs/files failed', err);
    }
  }, []);

  useEffect(() => {
    if (!open) return;
    refresh();
  }, [open, refresh]);

  useEffect(() => {
    return () => {
      streamAbort.current?.abort();
      uploadAbort.current?.abort();
    };
  }, []);

  const pickFile = () => inputRef.current?.click();

  const validateFile = (f: File): string | null => {
    const lower = f.name.toLowerCase();
    if (!ACCEPTED.some((ext) => lower.endsWith(ext))) {
      return `Estensione non ammessa (${f.name}). Consentite: ${ACCEPTED.join(', ')}`;
    }
    if (f.size > MAX_MB * 1024 * 1024) {
      return `File troppo grande (${f.name}, max ${MAX_MB} MB).`;
    }
    return null;
  };

  const handleFiles = (incoming: FileList | File[] | null) => {
    if (!incoming) return;
    const arr = Array.from(incoming);
    const accepted: File[] = [];
    for (const f of arr) {
      const err = validateFile(f);
      if (err) {
        toast.error(err);
        continue;
      }
      accepted.push(f);
    }
    if (accepted.length === 0) return;
    setFiles((prev) => {
      const seen = new Set(prev.map((p) => p.name));
      const merged = [...prev];
      for (const f of accepted) {
        if (!seen.has(f.name)) {
          merged.push(f);
          seen.add(f.name);
        }
      }
      return merged;
    });
  };

  const removeFile = (name: string) => {
    setFiles((prev) => prev.filter((f) => f.name !== name));
  };

  const clearFiles = () => setFiles([]);

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  const cancelUpload = () => {
    uploadAbort.current?.abort();
  };

  const subscribeJob = useCallback(
    async (jobId: string, initialJob: IngestJob) => {
      streamAbort.current?.abort();
      const ctrl = new AbortController();
      streamAbort.current = ctrl;
      try {
        await streamIngestJob(
          jobId,
          (ev) => {
            setEvents((prev) => [...prev, ev]);
            if (ev.type === 'final') {
              setActiveJob({ ...initialJob, ...ev });
              refresh();
              if (ev.status === 'done') onIngestComplete?.();
            } else if (ev.type === 'status') {
              setActiveJob((prev) =>
                prev ? { ...prev, status: ev.status, summary: ev.message } : prev,
              );
            }
          },
          ctrl.signal,
        );
      } catch (err) {
        if ((err as Error).name !== 'AbortError') console.warn('stream error', err);
      }
    },
    [onIngestComplete, refresh],
  );

  const replaceDoc = (idx: number, patch: Partial<DocUploadState>) => {
    setDocs((prev) => {
      const next = prev.slice();
      next[idx] = { ...next[idx], ...patch };
      return next;
    });
  };

  const startUpload = async () => {
    if (files.length === 0) return;
    setIsUploading(true);
    setEvents([]);
    setActiveJob(null);
    const initialDocs: DocUploadState[] = files.map((f) => ({
      filename: f.name,
      size: f.size,
      pct: 0,
      status: 'pending',
    }));
    setDocs(initialDocs);
    uploadAbort.current?.abort();
    const ctrl = new AbortController();
    uploadAbort.current = ctrl;

    let firstJobId: string | null = null;
    let firstInitialJob: IngestJob | null = null;

    const settled = await runWithConcurrency(files, UPLOAD_CONCURRENCY, async (file, i) => {
      replaceDoc(i, { status: 'uploading' });
      try {
        const res = await uploadRaw(file, options, {
          signal: ctrl.signal,
          onProgress: (p) => {
            replaceDoc(i, {
              pct: p.pct ?? Math.round((p.loaded / Math.max(1, file.size)) * 100),
            });
          },
        });
        replaceDoc(i, { pct: 100, status: 'done' });
        if (firstJobId === null) {
          firstJobId = res.job_id;
          firstInitialJob = {
            id: res.job_id,
            filename: res.filename,
            status: res.status,
            options: res.options,
            created_at: Date.now() / 1000,
            started_at: null,
            finished_at: null,
            backend: null,
            pages_written: 0,
            pages_needs_review: 0,
            pages_conflict: 0,
            pages_error: 0,
            errors: [],
            summary: '',
          };
        }
        return res;
      } catch (err) {
        const aborted = (err as Error)?.name === 'AbortError';
        const msg = aborted ? 'annullato' : err instanceof Error ? err.message : 'upload fallito';
        replaceDoc(i, { status: 'error', error: msg });
        throw err;
      }
    });

    setIsUploading(false);
    const okCount = settled.filter((s) => s.status === 'fulfilled').length;
    const koCount = settled.length - okCount;

    if (ctrl.signal.aborted) {
      toast.info('Upload annullato.');
    } else if (okCount > 0 && koCount === 0) {
      toast.success(`${okCount} document${okCount > 1 ? 'i' : 'o'} caricat${okCount > 1 ? 'i' : 'o'}. Ingestion avviata.`);
    } else if (okCount > 0) {
      toast.warning(`${okCount}/${files.length} caricati, ${koCount} fallit${koCount > 1 ? 'i' : 'o'}.`);
    } else {
      toast.error('Nessun upload completato.');
    }

    refresh();

    if (okCount > 0) {
      setFiles([]);
      setTab('history');
    }

    if (firstJobId && firstInitialJob) {
      setActiveJob(firstInitialJob);
      void subscribeJob(firstJobId, firstInitialJob);
    }
  };

  const onRetry = async (job: IngestJob) => {
    try {
      const r = await retryIngestJob(job.id);
      const initialJob: IngestJob = {
        ...job,
        id: r.job_id,
        status: 'queued',
        started_at: null,
        finished_at: null,
        pages_written: 0,
        pages_needs_review: 0,
        pages_conflict: 0,
        pages_error: 0,
        errors: [],
        summary: 'In coda…',
      };
      setActiveJob(initialJob);
      setEvents([]);
      setTab('history');
      toast.success(`Riprovo ${job.filename}.`);
      refresh();
      void subscribeJob(r.job_id, initialJob);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'retry fallito');
    }
  };

  const hasActiveJob = activeJob && activeJob.status !== 'done' && activeJob.status !== 'error';

  return (
    <ModalShell
      open={open}
      onClose={onClose}
      title="Carica documenti"
      subtitle="Aggiunge i contenuti alla knowledge base"
      icon={UploadIcon}
      width="2xl"
      panelClassName="max-h-[88vh]"
      headerActions={
        <IconButton
          icon={RefreshCw}
          aria-label="aggiorna lista"
          size="sm"
          onClick={() => refresh()}
        />
      }
    >
      <div className="flex items-center gap-1 border-b border-[var(--color-border)] px-5 pt-3">
        <TabButton active={tab === 'upload'} onClick={() => setTab('upload')}>
          Carica
        </TabButton>
        <TabButton active={tab === 'history'} onClick={() => setTab('history')}>
          Cronologia {jobs.length > 0 && `(${jobs.length})`}
        </TabButton>
        {hasActiveJob && (
          <span
            className="ml-auto inline-flex items-center gap-1.5 text-[10px] text-ink-muted"
            role="status"
            aria-live="polite"
          >
            <Loader2 size={11} className="animate-spin" aria-hidden />
            elaborazione in corso
          </span>
        )}
      </div>

      <div className="flex-1 overflow-y-auto">
        {tab === 'upload' ? (
          <UploadTab
            files={files}
            isDragging={isDragging}
            isUploading={isUploading}
            docs={docs}
            options={options}
            rawFiles={rawFiles}
            onPickFile={pickFile}
            onSetOptions={setOptions}
            onRemoveFile={removeFile}
            onClearFiles={clearFiles}
            onStart={startUpload}
            onCancel={cancelUpload}
            onDrop={onDrop}
            onDragEnter={() => setIsDragging(true)}
            onDragLeave={() => setIsDragging(false)}
            inputRef={inputRef}
            onFilesSelected={handleFiles}
          />
        ) : (
          <HistoryTab activeJob={activeJob} events={events} jobs={jobs} onRetry={onRetry} />
        )}
      </div>
    </ModalShell>
  );
}
