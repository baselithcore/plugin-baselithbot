export type DoneState =
  | 'ready' // ready to restart
  | 'sending' // SIGTERM sent
  | 'waiting' // polling backend up
  | 'ingesting' // backend up, watching ingest jobs
  | 'all_done' // ingest finished
  | 'error'
  | 'manual_required'; // bare process, no auto-restart possible

export interface IngestSnapshot {
  total: number; // unique filenames seen across the run
  done: number;
  running: number;
  errors: number;
  files: Array<{
    filename: string;
    status: 'queued' | 'running' | 'done' | 'error';
    pages_written: number;
    summary?: string;
  }>;
}
