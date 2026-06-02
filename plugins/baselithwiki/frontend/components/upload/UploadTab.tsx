import { FileText, Settings2, Upload as UploadIcon, X } from 'lucide-react';
import { useMemo, useState } from 'react';
import type { UploadRawOptions } from '../../lib/api';
import { cn } from '../../lib/cn';
import type { RawFileMeta } from '../../lib/types';
import { Button, Callout, IconButton, SectionHeader } from '../ui';
import { OptionRow } from './atoms';
import { ACCEPTED, MAX_MB } from './constants';
import { DocUploadList, type DocUploadState } from './DocUploadList';

interface UploadTabProps {
  files: File[];
  isDragging: boolean;
  isUploading: boolean;
  /** Per-file upload progress; empty until a batch starts. */
  docs: DocUploadState[];
  options: UploadRawOptions;
  rawFiles: RawFileMeta[];
  onPickFile: () => void;
  onSetOptions: (o: UploadRawOptions) => void;
  onRemoveFile: (name: string) => void;
  onClearFiles: () => void;
  onStart: () => void;
  onCancel: () => void;
  onDrop: (e: React.DragEvent) => void;
  onDragEnter: () => void;
  onDragLeave: () => void;
  inputRef: React.RefObject<HTMLInputElement | null>;
  onFilesSelected: (f: FileList | File[] | null) => void;
}

export function UploadTab({
  files,
  isDragging,
  isUploading,
  docs,
  options,
  rawFiles,
  onPickFile,
  onSetOptions,
  onRemoveFile,
  onClearFiles,
  onStart,
  onCancel,
  onDrop,
  onDragEnter,
  onDragLeave,
  inputRef,
  onFilesSelected,
}: UploadTabProps) {
  const [showOptions, setShowOptions] = useState(false);

  const dupNames = useMemo(() => {
    const existing = new Set(rawFiles.map((r) => r.name.toLowerCase()));
    return files.filter((f) => existing.has(f.name.toLowerCase())).map((f) => f.name);
  }, [files, rawFiles]);

  const totalMB = useMemo(() => files.reduce((s, f) => s + f.size, 0) / 1024 / 1024, [files]);

  return (
    <div className="space-y-5 px-5 py-4">
      <DropZone
        files={files}
        isDragging={isDragging}
        onPickFile={onPickFile}
        onRemoveFile={onRemoveFile}
        onClearFiles={onClearFiles}
        onDrop={onDrop}
        onDragEnter={onDragEnter}
        onDragLeave={onDragLeave}
        inputRef={inputRef}
        onFilesSelected={onFilesSelected}
        totalMB={totalMB}
      />

      {dupNames.length > 0 && (
        <Callout tone="warning">
          {dupNames.length === 1
            ? `Esiste già un file con lo stesso nome (${dupNames[0]}).`
            : `${dupNames.length} file hanno lo stesso nome di file già caricati.`}{' '}
          Attiva «Sostituisci file esistente» nelle opzioni per sovrascriverli.
        </Callout>
      )}

      <section>
        <SectionHeader
          title="Opzioni"
          icon={Settings2}
          trailing={
            <button
              type="button"
              onClick={() => setShowOptions((s) => !s)}
              className="focus-ring text-[10.5px] font-medium text-ink-muted hover:text-ink"
              aria-expanded={showOptions}
            >
              {showOptions ? 'Nascondi avanzate' : 'Mostra avanzate'}
            </button>
          }
        />
        <OptionRow
          label="Rendi disponibile alla chat dopo l'elaborazione"
          hint="Indicizza le pagine generate. Disattiva solo se vuoi processare offline."
          checked={options.reindex ?? true}
          onChange={(v) => onSetOptions({ ...options, reindex: v })}
        />
        {showOptions && (
          <div className="mt-2.5 space-y-2.5">
            <OptionRow
              label="Solo pagina sorgente (più veloce)"
              hint="Genera la sola pagina sorgente, salta entità e concetti correlati. Utile per un primo pass."
              checked={options.only_source_page ?? false}
              onChange={(v) => onSetOptions({ ...options, only_source_page: v })}
            />
            <OptionRow
              label="Anteprima senza scrittura"
              hint="Esegue la pipeline ma non salva nulla. Usalo per stimare tempi e qualità."
              checked={options.dry_run ?? false}
              onChange={(v) => onSetOptions({ ...options, dry_run: v })}
            />
            <OptionRow
              label="Sovrascrivi pagine esistenti"
              hint="Rimpiazza le pagine generate in precedenza. Disattivato: salva la nuova versione affianco per una revisione manuale."
              checked={options.overwrite ?? false}
              onChange={(v) => onSetOptions({ ...options, overwrite: v })}
            />
            <OptionRow
              label="Sostituisci file esistente"
              hint="Sovrascrive un file precedentemente caricato con lo stesso nome. Da usare solo se necessario."
              checked={options.replace_existing ?? false}
              onChange={(v) => onSetOptions({ ...options, replace_existing: v })}
              warn
            />
          </div>
        )}
      </section>

      {(isUploading || docs.length > 0) && <DocUploadList docs={docs} />}

      <div className="flex items-center justify-between gap-3 border-t border-[var(--color-border)] pt-3">
        <div className="text-[10.5px] leading-relaxed text-ink-subtle">
          L'elaborazione di un PDF richiede in media 2–10 minuti. Puoi seguirne il progresso nella
          cronologia.
        </div>
        <div className="inline-flex items-center gap-2">
          {isUploading && (
            <Button variant="secondary" leadingIcon={X} onClick={onCancel}>
              Annulla
            </Button>
          )}
          <Button
            variant="primary"
            leadingIcon={UploadIcon}
            disabled={files.length === 0}
            loading={isUploading}
            onClick={onStart}
          >
            {isUploading
              ? 'Caricamento…'
              : files.length > 1
                ? `Avvia elaborazione (${files.length})`
                : 'Avvia elaborazione'}
          </Button>
        </div>
      </div>
    </div>
  );
}

interface DropZoneProps {
  files: File[];
  isDragging: boolean;
  totalMB: number;
  onPickFile: () => void;
  onRemoveFile: (name: string) => void;
  onClearFiles: () => void;
  onDrop: (e: React.DragEvent) => void;
  onDragEnter: () => void;
  onDragLeave: () => void;
  inputRef: React.RefObject<HTMLInputElement | null>;
  onFilesSelected: (f: FileList | File[] | null) => void;
}

function DropZone({
  files,
  isDragging,
  totalMB,
  onPickFile,
  onRemoveFile,
  onClearFiles,
  onDrop,
  onDragEnter,
  onDragLeave,
  inputRef,
  onFilesSelected,
}: DropZoneProps) {
  const hasFiles = files.length > 0;
  return (
    <div
      onDrop={onDrop}
      onDragOver={(e) => {
        e.preventDefault();
        onDragEnter();
      }}
      onDragEnter={(e) => {
        e.preventDefault();
        onDragEnter();
      }}
      onDragLeave={onDragLeave}
      onClick={hasFiles ? undefined : onPickFile}
      onKeyDown={(e) => {
        if (!hasFiles && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault();
          onPickFile();
        }
      }}
      role={hasFiles ? undefined : 'button'}
      tabIndex={hasFiles ? undefined : 0}
      aria-label={hasFiles ? undefined : 'seleziona o trascina file'}
      className={cn(
        'focus-ring rounded-lg border-2 border-dashed p-4 transition-colors',
        hasFiles ? 'cursor-default' : 'cursor-pointer p-8 text-center',
        isDragging
          ? 'border-[var(--color-brand)] bg-[var(--color-brand-soft)]'
          : 'border-[var(--color-border)] hover:border-[var(--color-brand-ring)] hover:bg-[var(--color-surface)]'
      )}
    >
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED.join(',')}
        multiple
        hidden
        onChange={(e) => {
          onFilesSelected(e.target.files);
          e.target.value = '';
        }}
      />
      {hasFiles ? (
        <div className="space-y-2.5">
          <div className="flex items-center justify-between text-[11px]">
            <span className="font-semibold">
              {files.length} file selezionat{files.length > 1 ? 'i' : 'o'}
              <span className="ml-2 font-normal tabular-nums text-ink-subtle">
                {totalMB.toFixed(2)} MB totali
              </span>
            </span>
            <div className="inline-flex items-center gap-1">
              <button
                type="button"
                onClick={onPickFile}
                className="focus-ring text-[10.5px] font-medium text-[var(--color-brand)] hover:underline"
              >
                Aggiungi…
              </button>
              <span className="text-ink-subtle">·</span>
              <button
                type="button"
                onClick={onClearFiles}
                className="focus-ring text-[10.5px] font-medium text-ink-muted hover:text-ink"
              >
                Rimuovi tutti
              </button>
            </div>
          </div>
          <ul className="rounded-md border border-[var(--color-border)] divide-y divide-[var(--color-border)] max-h-44 overflow-y-auto">
            {files.map((f) => (
              <li key={f.name} className="flex items-center gap-2 px-2.5 py-1.5 text-[11px]">
                <FileText size={12} className="shrink-0 text-[var(--color-brand)]" aria-hidden />
                <span className="flex-1 truncate font-mono">{f.name}</span>
                <span className="text-[10px] tabular-nums text-ink-subtle">
                  {(f.size / 1024 / 1024).toFixed(2)} MB
                </span>
                <IconButton
                  icon={X}
                  aria-label={`rimuovi ${f.name}`}
                  size="sm"
                  onClick={() => onRemoveFile(f.name)}
                />
              </li>
            ))}
          </ul>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-2 text-ink-muted">
          <UploadIcon size={22} className="text-[var(--color-brand)]" aria-hidden />
          <div className="text-sm font-medium text-ink">
            Trascina qui i PDF o clicca per sfogliare
          </div>
          <div className="text-[11px] text-ink-subtle">
            Solo PDF · max {MAX_MB} MB per file · selezione multipla supportata
          </div>
        </div>
      )}
    </div>
  );
}
