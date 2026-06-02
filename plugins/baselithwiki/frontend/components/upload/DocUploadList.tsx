import { AlertCircle, CheckCircle2, FileText, Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';
import { cn } from '../../lib/cn';

export interface DocUploadState {
  filename: string;
  size: number;
  pct: number;
  status: 'pending' | 'uploading' | 'done' | 'error';
  error?: string;
}

/**
 * Per-file progress list. Each row updates its bytes-uploaded percentage
 * live, status icon flips when the request resolves. Used by the setup
 * wizard's scaffold-apply phase and the post-wizard upload modal.
 */
export function DocUploadList({ docs }: { docs: DocUploadState[] }) {
  if (docs.length === 0) return null;
  const totalBytes = docs.reduce((s, d) => s + d.size, 0);
  const uploadedBytes = docs.reduce((s, d) => s + (d.size * d.pct) / 100, 0);
  const overallPct =
    totalBytes > 0 ? Math.min(100, Math.round((uploadedBytes / totalBytes) * 100)) : 0;
  const done = docs.filter((d) => d.status === 'done').length;
  const errored = docs.filter((d) => d.status === 'error').length;
  const uploading = docs.filter((d) => d.status === 'uploading').length;

  return (
    <section
      className="rounded-lg border border-[var(--color-border)] bg-[var(--color-canvas)] p-3 space-y-2.5"
      role="status"
      aria-live="polite"
    >
      <div className="flex items-center justify-between text-[11px]">
        <div className="inline-flex items-center gap-1.5 font-semibold">
          <FileText size={12} className="text-[var(--color-brand)]" />
          Upload documenti
        </div>
        <span className="text-ink-subtle tabular-nums">
          {done}/{docs.length}
          {errored > 0 && <span className="text-[var(--color-danger)]"> · {errored} ko</span>}
          {uploading > 0 && (
            <span className="text-[var(--color-brand)]"> · {uploading} in corso</span>
          )}
        </span>
      </div>

      <div
        className="h-1.5 w-full rounded-full bg-[var(--color-surface)] overflow-hidden"
        role="progressbar"
        aria-valuenow={overallPct}
        aria-valuemin={0}
        aria-valuemax={100}
      >
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${overallPct}%` }}
          transition={{ duration: 0.2, ease: 'linear' }}
          className={cn(
            'h-full',
            errored > 0 && done + errored === docs.length
              ? 'bg-[var(--color-warning)] transition-colors duration-200'
              : 'bg-[var(--color-brand)]'
          )}
        />
      </div>

      <ul className="rounded-md border border-[var(--color-border)] divide-y divide-[var(--color-border)] max-h-44 overflow-y-auto">
        {docs.map((d) => (
          <li key={d.filename} className="flex items-center gap-2 px-2.5 py-1.5 text-[11px]">
            <DocStatusIcon status={d.status} />
            <span className="flex-1 truncate font-mono">{d.filename}</span>
            <span className="text-[10px] text-ink-subtle tabular-nums w-12 text-right">
              {d.status === 'done'
                ? '100%'
                : d.status === 'error'
                  ? (d.error ?? 'errore')
                  : `${d.pct}%`}
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}

function DocStatusIcon({ status }: { status: DocUploadState['status'] }) {
  if (status === 'done')
    return <CheckCircle2 size={12} className="text-[var(--color-success)] shrink-0" />;
  if (status === 'error')
    return <AlertCircle size={12} className="text-[var(--color-danger)] shrink-0" />;
  if (status === 'uploading')
    return <Loader2 size={12} className="animate-spin text-[var(--color-brand)] shrink-0" />;
  return <span className="size-3 shrink-0 rounded-full border border-[var(--color-border)]" />;
}
