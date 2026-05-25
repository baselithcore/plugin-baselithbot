import { ArrowLeft, ExternalLink, FileText } from 'lucide-react';
import { rawFileUrl } from '../../lib/api';
import type { Source } from '../../lib/types';

export function PreviewHeader({
  title,
  docId,
  source,
  obsidianUri,
  onBack,
}: {
  title: string;
  docId: string;
  source: Source | null;
  obsidianUri: string | null;
  onBack: () => void;
}) {
  return (
    <div className="border-b border-[var(--color-border)] bg-[var(--color-canvas-raised)] px-4 py-3">
      <div className="flex items-start gap-2">
        <button
          onClick={onBack}
          className="focus-ring sm:hidden shrink-0 -ml-1 inline-flex size-7 items-center justify-center
                     rounded-md text-ink-subtle hover:bg-[var(--color-surface)] hover:text-ink"
          aria-label="torna all'elenco fonti"
        >
          <ArrowLeft size={14} />
        </button>
        <div className="min-w-0 flex-1">
          <div className="text-sm font-semibold leading-tight text-ink break-words">{title}</div>
          <div className="mt-0.5 text-[11px] font-mono text-ink-subtle truncate" title={docId}>
            {docId}
          </div>
          {source?.edizione && (
            <div className="mt-1 text-[10px] text-ink-subtle">
              Edizione <span className="font-medium text-ink">{source.edizione}</span>
              {source.stato && ` · ${source.stato}`}
            </div>
          )}
        </div>
      </div>
      {(source?.source_file || obsidianUri) && (
        <div className="mt-2 flex flex-wrap items-center gap-1.5">
          {source?.source_file && (
            <a
              href={rawFileUrl(source.source_file)}
              target="_blank"
              rel="noopener noreferrer"
              className="focus-ring inline-flex items-center gap-1 rounded-md
                         border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1
                         text-[10px] font-medium text-ink-muted hover:text-ink"
              title={
                source.source_pages_count
                  ? `apri originale (${source.source_pages_count} pagine)`
                  : 'apri file originale'
              }
            >
              <FileText size={10} aria-hidden /> Originale
              {source.source_pages_count ? ` (${source.source_pages_count}p)` : ''}
            </a>
          )}
          {obsidianUri && (
            <a
              href={obsidianUri}
              className="focus-ring inline-flex items-center gap-1 rounded-md
                         border border-[var(--color-border)] bg-[var(--color-surface)] px-2 py-1
                         text-[10px] font-medium text-ink-muted hover:text-ink"
              title="apri in Obsidian"
            >
              Obsidian <ExternalLink size={10} aria-hidden />
            </a>
          )}
        </div>
      )}
    </div>
  );
}
