import { Database, FolderTree } from 'lucide-react';
import { Callout } from '../../ui';
import { Field, type StepProps } from '../atoms';
import { DEFAULT_FORM } from '../schema';

export function VaultStep({ register, errors, values }: StepProps) {
  const v = values ?? DEFAULT_FORM;
  return (
    <div className="space-y-5 px-5 py-4">
      <Callout tone="info" icon={Database} title="Spazio di archiviazione">
        Il vault è la cartella locale che ospita documenti sorgente, pagine generate e log operativi
        della knowledge base.
      </Callout>

      <Field
        label="Percorso vault"
        hint="Percorso assoluto. Lascia vuoto per usare la cartella predefinita."
        error={errors.vault_root?.message}
        full
      >
        <input
          {...register('vault_root')}
          placeholder={v.name ? `~/wikis/${v.name}` : '~/wikis/legal'}
          className="input font-mono text-[11.5px]"
          autoComplete="off"
          spellCheck={false}
        />
      </Field>

      <details className="group rounded-lg border border-[var(--color-border)] bg-[var(--color-surface)]">
        <summary className="cursor-pointer list-none px-3 py-2 text-[11px] font-semibold text-ink flex items-center gap-1.5">
          <FolderTree size={12} className="text-[var(--color-brand)]" aria-hidden />
          Cosa viene creato nella cartella
          <span className="ml-auto text-[10px] font-normal text-ink-subtle group-open:hidden">
            mostra
          </span>
          <span className="ml-auto hidden text-[10px] font-normal text-ink-subtle group-open:inline">
            nascondi
          </span>
        </summary>
        <div className="border-t border-[var(--color-border)] px-3 py-2.5 space-y-2">
          <pre className="font-mono text-[10.5px] leading-relaxed text-ink-muted whitespace-pre">
            {`<vault>/
├── raw/         documenti sorgente (PDF caricati dal wizard o aggiunti dopo)
└── wiki/        pagine markdown generate dal modello`}
          </pre>
          <p className="text-[10.5px] leading-relaxed text-ink-subtle">
            La cartella <code>raw/</code> resta sorgente di verità: i documenti non vengono
            modificati. Le pagine consultabili dalla chat vivono in <code>wiki/</code>.
          </p>
        </div>
      </details>

      <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-[var(--color-border)] bg-[var(--color-canvas-raised)] px-3 py-2.5 hover:bg-[var(--color-surface)]">
        <input
          type="checkbox"
          {...register('activate')}
          className="mt-0.5 accent-[var(--color-brand)]"
        />
        <div className="min-w-0">
          <div className="text-xs font-medium">Imposta come wiki attiva</div>
          <div className="mt-0.5 text-[10.5px] leading-relaxed text-ink-subtle">
            Subito dopo lo scaffold il sistema viene riavviato per caricarla. Se preferisci, puoi
            attivarla in un secondo momento.
          </div>
        </div>
      </label>
    </div>
  );
}
