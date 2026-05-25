import { FileText, UploadCloud, X } from 'lucide-react';
import { useRef, useState } from 'react';
import { toast } from 'sonner';
import { cn } from '../../../lib/cn';
import { Callout, IconButton, SectionHeader } from '../../ui';

export function DocumentsStep({
  docFiles,
  setDocFiles,
}: {
  docFiles: File[];
  setDocFiles: (f: File[]) => void;
}) {
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const totalMB = docFiles.reduce((s, f) => s + f.size, 0) / 1024 / 1024;

  const onAdd = (files: FileList | File[] | null) => {
    if (!files) return;
    const incoming = Array.from(files);
    const valid: File[] = [];
    for (const f of incoming) {
      if (!/\.pdf$/i.test(f.name)) {
        toast.error(`${f.name}: solo PDF ammessi`);
        continue;
      }
      if (f.size > 50 * 1024 * 1024) {
        toast.error(`${f.name}: > 50 MB`);
        continue;
      }
      if (docFiles.some((d) => d.name === f.name)) continue;
      valid.push(f);
    }
    if (valid.length > 0) setDocFiles([...docFiles, ...valid]);
  };

  return (
    <div className="px-5 py-4 space-y-4">
      <Callout tone="info" icon={FileText} title="Documenti iniziali">
        Carica i PDF da rendere subito consultabili. Verranno trasformati in pagine al primo
        avvio. Puoi sempre aggiungerne altri in seguito.
      </Callout>

      <div
        onDragOver={(e) => {
          e.preventDefault();
          setIsDragging(true);
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          onAdd(e.dataTransfer.files);
        }}
        onClick={() => inputRef.current?.click()}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            inputRef.current?.click();
          }
        }}
        role="button"
        tabIndex={0}
        aria-label="seleziona o trascina documenti"
        className={cn(
          'focus-ring cursor-pointer rounded-lg border-2 border-dashed p-6 text-center transition-colors',
          isDragging
            ? 'border-[var(--color-brand)] bg-[var(--color-brand-soft)]'
            : 'border-[var(--color-border)] hover:border-[var(--color-brand-ring)] hover:bg-[var(--color-surface)]',
        )}
      >
        <input
          ref={inputRef}
          type="file"
          accept=".pdf"
          multiple
          hidden
          onChange={(e) => {
            onAdd(e.target.files);
            e.target.value = '';
          }}
        />
        <UploadCloud size={22} className="mx-auto text-[var(--color-brand)]" aria-hidden />
        <div className="mt-1.5 text-[12.5px] font-medium">
          Trascina i PDF o clicca per selezionarli
        </div>
        <div className="text-[10.5px] text-ink-subtle">Solo PDF · max 50 MB ciascuno</div>
      </div>

      {docFiles.length > 0 && (
        <section>
          <SectionHeader
            title={`File selezionati (${docFiles.length})`}
            trailing={
              <span className="text-[10px] tabular-nums text-ink-subtle">
                tot {totalMB.toFixed(1)} MB
              </span>
            }
          />
          <ul className="overflow-hidden rounded-lg border border-[var(--color-border)] divide-y divide-[var(--color-border)]">
            {docFiles.map((f, i) => (
              <li key={`${f.name}-${i}`} className="flex items-center gap-2 px-3 py-2 text-[11px]">
                <FileText size={12} className="shrink-0 text-[var(--color-brand)]" aria-hidden />
                <span className="flex-1 truncate font-mono">{f.name}</span>
                <span className="tabular-nums text-ink-subtle">
                  {(f.size / 1024 / 1024).toFixed(2)} MB
                </span>
                <IconButton
                  icon={X}
                  aria-label={`rimuovi ${f.name}`}
                  size="sm"
                  onClick={(e) => {
                    e.stopPropagation();
                    setDocFiles(docFiles.filter((_, j) => j !== i));
                  }}
                />
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
