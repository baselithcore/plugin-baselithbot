import { useCallback, useEffect, useRef, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api, type ScanResult } from '../lib/api';
import { Card, EmptyState, Icon, PageHeader, SeverityBadge } from '../components/ui';

const ACCEPTED_EXT = [
  '.exe',
  '.dll',
  '.sys',
  '.ocx',
  '.scr',
  '.so',
  '.elf',
  '.bin',
  '.out',
  '.dylib',
  '.macho',
  '.apk',
  '.jar',
  '.class',
  '.dex',
  '.pyc',
  '.ps1',
  '.vbs',
  '.js',
  '.bat',
  '.cmd',
  '.doc',
  '.docx',
  '.xls',
  '.xlsx',
  '.ppt',
  '.pptx',
  '.pdf',
  '.rtf',
  '.zip',
  '.7z',
  '.tar',
  '.gz',
  '.rar',
  '.iso',
  '.img',
];

interface QueuedJob {
  id: string;
  filename: string;
  size: number;
  sha256: string;
  scanId: string;
  status: 'uploading' | 'queued' | 'running' | 'completed' | 'failed';
  startedAt: number;
  result?: ScanResult;
  error?: string;
}

export function BinaryScan() {
  const navigate = useNavigate();
  const [jobs, setJobs] = useState<QueuedJob[]>([]);
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const updateJob = useCallback((id: string, patch: Partial<QueuedJob>) => {
    setJobs((cur) => cur.map((j) => (j.id === id ? { ...j, ...patch } : j)));
  }, []);

  const handleFiles = useCallback(
    async (files: FileList | File[]) => {
      const list = Array.from(files);
      for (const file of list) {
        const id = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
        const job: QueuedJob = {
          id,
          filename: file.name,
          size: file.size,
          sha256: '',
          scanId: '',
          status: 'uploading',
          startedAt: Date.now(),
        };
        setJobs((cur) => [job, ...cur]);
        try {
          const res = await api.uploadFileForScan(file);
          updateJob(id, {
            sha256: res.sha256,
            scanId: res.scan_id,
            status: 'queued',
          });
        } catch (err) {
          updateJob(id, {
            status: 'failed',
            error: err instanceof Error ? err.message : String(err),
          });
        }
      }
    },
    [updateJob]
  );

  // Poll active scans until terminal — websocket would be ideal but the
  // existing scan WS is tied to a different shell; polling keeps this
  // route self-contained and avoids new infra.
  useEffect(() => {
    const active = jobs.filter(
      (j) => j.scanId && j.status !== 'completed' && j.status !== 'failed'
    );
    if (!active.length) return;
    let cancelled = false;
    const tick = async () => {
      for (const job of active) {
        try {
          const result = await api.getScan(job.scanId);
          if (cancelled) return;
          if (result.status === 'completed' || result.status === 'failed') {
            updateJob(job.id, { status: result.status, result });
          } else if (result.status === 'running') {
            updateJob(job.id, { status: 'running' });
          }
        } catch {
          /* keep polling */
        }
      }
    };
    void tick();
    const handle = setInterval(tick, 2000);
    return () => {
      cancelled = true;
      clearInterval(handle);
    };
  }, [jobs, updateJob]);

  const onDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (e.dataTransfer.files.length) void handleFiles(e.dataTransfer.files);
    },
    [handleFiles]
  );

  return (
    <div className="space-y-6">
      <PageHeader
        title="Binary analysis"
        description="Drop an executable, library, document, or archive — the static analyzer extracts hashes, IOCs, sections, imports and YARA matches without ever running the sample."
        badge={{ label: 'enterprise', tone: 'live' }}
      />

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={onDrop}
        onClick={() => inputRef.current?.click()}
        className={`relative cursor-pointer rounded-lg border-2 border-dashed transition-all ${
          dragOver
            ? 'border-brand bg-brand/5 shadow-glow-soft'
            : 'border-bg-line bg-bg-elevated/40 hover:border-bg-line-strong hover:bg-bg-elevated/70'
        }`}
      >
        <input
          ref={inputRef}
          type="file"
          multiple
          accept={ACCEPTED_EXT.join(',')}
          className="sr-only"
          onChange={(e) => {
            if (e.target.files) void handleFiles(e.target.files);
            e.target.value = '';
          }}
        />
        <div className="flex flex-col items-center gap-3 px-6 py-14 text-center">
          <div className="grid h-14 w-14 place-items-center rounded-full bg-brand/10 ring-1 ring-brand/30">
            <Icon.Inbox size={28} />
          </div>
          <div className="space-y-1">
            <div className="font-display text-lg font-semibold text-text-primary">
              Drop samples to analyze
            </div>
            <div className="text-sm text-text-secondary">
              Or click to choose files. Supports PE, ELF, Mach-O, .NET, APK, Office, PDF, archives.
              Max 256 MiB per file.
            </div>
          </div>
          <div className="flex flex-wrap items-center justify-center gap-1.5 text-2xs text-text-muted">
            {['.exe', '.dll', '.so', '.elf', '.macho', '.apk', '.pdf', '.docx', '.zip'].map(
              (ext) => (
                <span
                  key={ext}
                  className="rounded border border-bg-line bg-bg-base/60 px-1.5 py-0.5 font-mono"
                >
                  {ext}
                </span>
              )
            )}
          </div>
        </div>
      </div>

      <div className="grid gap-4">
        {jobs.length === 0 ? (
          <Card>
            <EmptyState
              title="No samples analyzed yet"
              description="Drop files above to start the static-analysis pipeline. Each upload is hashed, quarantined with 0600 permissions, then dispatched to the binary analyzer."
            />
          </Card>
        ) : (
          jobs.map((job) => (
            <JobCard key={job.id} job={job} onOpenScan={(id) => navigate(`/scans/${id}`)} />
          ))
        )}
      </div>
    </div>
  );
}

function JobCard({ job, onOpenScan }: { job: QueuedJob; onOpenScan: (scanId: string) => void }) {
  const sevCounts = (job.result?.findings ?? []).reduce<Record<string, number>>((acc, f) => {
    acc[f.severity] = (acc[f.severity] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <Card>
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1 space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-sm text-text-primary truncate">{job.filename}</span>
            <span className="text-2xs text-text-muted">{formatSize(job.size)}</span>
            <StatusPill status={job.status} />
          </div>
          {job.sha256 && (
            <div className="font-mono text-2xs text-text-muted truncate">sha256:{job.sha256}</div>
          )}
          {job.error && <div className="text-xs text-sev-critical font-mono">{job.error}</div>}
          {job.result && job.result.findings.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5">
              {(['critical', 'high', 'medium', 'low', 'info'] as const).map((s) =>
                sevCounts[s] ? (
                  <span key={s} className="flex items-center gap-1">
                    <SeverityBadge severity={s} />
                    <span className="text-xs text-text-secondary">{sevCounts[s]}</span>
                  </span>
                ) : null
              )}
            </div>
          )}
        </div>
        <div className="flex flex-shrink-0 flex-col items-end gap-2">
          {job.scanId ? (
            <Link
              to={`/scans/${job.scanId}`}
              className="ra-btn ra-btn-secondary text-xs"
              onClick={(e) => {
                e.preventDefault();
                onOpenScan(job.scanId);
              }}
            >
              Open report
              <Icon.ArrowRight size={14} />
            </Link>
          ) : (
            <span className="text-2xs text-text-muted">awaiting scan_id…</span>
          )}
        </div>
      </div>

      {job.status === 'uploading' || job.status === 'queued' || job.status === 'running' ? (
        <div className="mt-3 h-1 w-full overflow-hidden rounded-full bg-bg-overlay">
          <div className="h-full w-1/3 animate-pulse bg-brand" />
        </div>
      ) : null}

      {job.result?.findings && job.result.findings.length > 0 && (
        <div className="mt-3 grid gap-2">
          {job.result.findings.slice(0, 5).map((f) => (
            <div
              key={f.id}
              className="rounded border border-bg-line bg-bg-base/60 px-3 py-2 text-xs"
            >
              <div className="flex items-center justify-between gap-2">
                <span className="font-medium text-text-primary truncate">{f.title}</span>
                <SeverityBadge severity={f.severity} />
              </div>
              {f.description && (
                <div className="mt-1 line-clamp-2 text-text-secondary">{f.description}</div>
              )}
            </div>
          ))}
          {job.result.findings.length > 5 && (
            <div className="text-2xs text-text-muted">
              +{job.result.findings.length - 5} more — open report for full detail.
            </div>
          )}
        </div>
      )}
    </Card>
  );
}

function StatusPill({ status }: { status: QueuedJob['status'] }) {
  const tone =
    status === 'completed'
      ? 'bg-status-success/15 text-status-success'
      : status === 'failed'
        ? 'bg-sev-critical/15 text-sev-critical'
        : 'bg-bg-overlay text-text-secondary';
  return <span className={`rounded px-1.5 py-0.5 font-mono text-2xs ${tone}`}>{status}</span>;
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`;
}
