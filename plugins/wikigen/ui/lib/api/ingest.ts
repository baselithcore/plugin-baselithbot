import type { IngestJob, IngestStreamEvent, RawFileMeta } from '../types';
import { ApiError, BASE, json } from './client';
import { postFormWithProgress, type UploadOptions } from './_upload';

export interface UploadRawOptions {
  overwrite?: boolean;
  reindex?: boolean;
  dry_run?: boolean;
  only_source_page?: boolean;
  replace_existing?: boolean;
}

export interface UploadRawResponse {
  job_id: string;
  filename: string;
  size: number;
  status: IngestJob['status'];
  options: IngestJob['options'];
}

/**
 * Upload multipart di un PDF in `raw/` + lancia ingest in background.
 * Ritorna subito con `job_id`; usa `streamIngestJob` per ricevere eventi live.
 *
 * `uploadOpts.onProgress` riceve i bytes-uploaded events (XHR-based — fetch
 * non supporta progress request-side). `uploadOpts.signal` aborta upload
 * in volo (AbortController.abort()).
 */
export function uploadRaw(
  file: File,
  opts: UploadRawOptions = {},
  uploadOpts: UploadOptions = {}
): Promise<UploadRawResponse> {
  const fd = new FormData();
  fd.append('file', file);
  if (opts.overwrite !== undefined) fd.append('overwrite', String(opts.overwrite));
  if (opts.reindex !== undefined) fd.append('reindex', String(opts.reindex));
  if (opts.dry_run !== undefined) fd.append('dry_run', String(opts.dry_run));
  if (opts.only_source_page !== undefined)
    fd.append('only_source_page', String(opts.only_source_page));
  if (opts.replace_existing !== undefined)
    fd.append('replace_existing', String(opts.replace_existing));
  return postFormWithProgress<UploadRawResponse>('/ingest/raw', fd, uploadOpts);
}

export function fetchJobs(
  limit = 20,
  signal?: AbortSignal
): Promise<{ count: number; jobs: IngestJob[] }> {
  return json(`/ingest/raw/jobs?limit=${limit}`, { signal });
}

export function fetchJob(jobId: string, signal?: AbortSignal): Promise<IngestJob> {
  return json<IngestJob>(`/ingest/raw/jobs/${encodeURIComponent(jobId)}`, { signal });
}

export function fetchRawFiles(
  signal?: AbortSignal
): Promise<{ count: number; pending_count: number; files: RawFileMeta[] }> {
  return json('/raw/files', { signal });
}

/**
 * Streaming NDJSON degli eventi di un ingest job. Replay history + live.
 * Termina quando il backend chiude lo stream (job done/error).
 */
export async function streamIngestJob(
  jobId: string,
  onEvent: (ev: IngestStreamEvent) => void,
  signal?: AbortSignal
): Promise<void> {
  const res = await fetch(`${BASE}/ingest/raw/jobs/${encodeURIComponent(jobId)}/stream`, {
    method: 'GET',
    signal,
  });
  if (!res.ok || !res.body) {
    throw new ApiError(res.status, `stream error ${res.status}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      buffer += decoder.decode();
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    let newlineIdx: number;
    while ((newlineIdx = buffer.indexOf('\n')) >= 0) {
      const line = buffer.slice(0, newlineIdx).trim();
      buffer = buffer.slice(newlineIdx + 1);
      if (!line) continue;
      try {
        onEvent(JSON.parse(line) as IngestStreamEvent);
      } catch (err) {
        console.warn('ingest stream parse failed', err, line);
      }
    }
  }
  if (buffer.trim()) {
    try {
      onEvent(JSON.parse(buffer) as IngestStreamEvent);
    } catch {
      /* noop */
    }
  }
}

export interface PendingRawResponse {
  count: number;
  files: { name: string; size: number; modified: number }[];
}

export function fetchPendingRaw(signal?: AbortSignal): Promise<PendingRawResponse> {
  return json<PendingRawResponse>('/ingest/raw/pending', { signal });
}

export interface IngestFromDiskResponse {
  started: number;
  jobs: { job_id: string; filename: string }[];
}

/**
 * Trigger the full ingest pipeline on PDFs already deposited in raw/.
 * `filename=null` ingests every *.pdf in raw/.
 */
export function ingestRawFromDisk(
  filename: string | null = null,
  signal?: AbortSignal,
  opts: { overwrite?: boolean; reindex?: boolean } = {},
): Promise<IngestFromDiskResponse> {
  const params = new URLSearchParams();
  if (filename) params.set('filename', filename);
  if (opts.overwrite !== undefined) params.set('overwrite', String(opts.overwrite));
  if (opts.reindex !== undefined) params.set('reindex', String(opts.reindex));
  return json(`/ingest/raw/from-disk${params.toString() ? `?${params}` : ''}`, {
    method: 'POST',
    signal,
  });
}

/**
 * Retry an ingest job by re-running the pipeline against the same PDF in raw/.
 * Returns the spawned job id. Sets overwrite=true since the user is explicitly
 * retrying and expects the previous output to be replaced.
 */
export async function retryIngestJob(
  jobId: string,
  signal?: AbortSignal,
): Promise<{ job_id: string; filename: string }> {
  const job = await fetchJob(jobId, signal);
  const r = await ingestRawFromDisk(job.filename, signal, { overwrite: true });
  if (!r.jobs.length) {
    throw new ApiError(404, `nessun file ${job.filename} in raw/`);
  }
  return r.jobs[0];
}
