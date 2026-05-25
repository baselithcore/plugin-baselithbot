import { KeyRound, MessageSquare, Server, Workflow } from 'lucide-react';
import { Callout } from '../../ui';
import { Field, type StepProps } from '../atoms';
import { DEFAULT_FORM } from '../schema';

export function ProviderStep({
  register,
  errors,
  values,
  showProvider,
  setShowProvider,
}: StepProps & {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  setValue: any;
  showProvider: boolean;
  setShowProvider: (v: boolean) => void;
}) {
  const v = values ?? DEFAULT_FORM;
  const ragVendor = v.provider_rag_vendor ?? v.provider_vendor ?? 'ollama';
  const ingestVendor = v.provider_ingest_vendor ?? v.provider_vendor ?? 'ollama';
  const isSplit = ragVendor !== ingestVendor;
  const needsOllama = ragVendor === 'ollama' || ingestVendor === 'ollama';
  const needsOpenai = ragVendor === 'openai' || ingestVendor === 'openai';

  return (
    <div className="space-y-4 px-5 py-4">
      <Callout tone="info" icon={Server} title="Provider del modello">
        Scegli il vendor indipendentemente per chat e ingestion. Esempio: Ollama locale per la chat
        (privacy / latenza) + OpenAI per ingestion (qualità classify/plan), o viceversa.
      </Callout>

      <label className="flex cursor-pointer items-start gap-3 rounded-lg border border-[var(--color-border)] bg-[var(--color-canvas-raised)] px-3 py-2.5 hover:bg-[var(--color-surface)]">
        <input
          type="checkbox"
          {...register('use_provider')}
          className="mt-0.5 accent-[var(--color-brand)]"
          onChange={(e) => {
            (register('use_provider').onChange as (e: unknown) => void)(e);
            setShowProvider(e.target.checked);
          }}
        />
        <div className="min-w-0">
          <div className="flex items-center gap-1.5 text-xs font-medium">
            <KeyRound size={12} className="text-[var(--color-brand)]" aria-hidden />
            Configura il provider in questo passaggio
          </div>
          <div className="mt-0.5 text-[10.5px] leading-relaxed text-ink-subtle">
            Salva vendor, modello e indirizzo del servizio. Le credenziali esistenti vengono
            sovrascritte solo se inserisci nuovi valori qui.
          </div>
        </div>
      </label>

      {(showProvider || v.use_provider) && (
        <div className="space-y-3 rounded-lg border border-[var(--color-border)] px-3 py-3">
          {/* Chat / RAG phase card */}
          <div className="space-y-2.5 rounded-md border border-[var(--color-border)] bg-[var(--color-canvas-raised)] px-3 py-2.5">
            <div className="flex items-center gap-1.5 text-[11.5px] font-semibold text-ink">
              <MessageSquare size={13} className="text-[var(--color-brand)]" />
              Chat / RAG
              <span className="text-[10px] font-normal text-ink-subtle">
                — usato per generare le risposte
              </span>
            </div>
            <Field label="Vendor" error={errors.provider_rag_vendor?.message}>
              <select {...register('provider_rag_vendor')} className="input">
                <option value="ollama">Ollama (locale)</option>
                <option value="openai">OpenAI</option>
              </select>
            </Field>
            <Field
              label="Modello"
              hint={
                ragVendor === 'openai'
                  ? 'Es. gpt-4o-mini, gpt-4o.'
                  : 'Es. llama3.1:8b, qwen2.5:7b-instruct.'
              }
              error={errors.provider_model?.message}
            >
              <input
                {...register('provider_model')}
                className="input font-mono text-[11.5px]"
                placeholder={ragVendor === 'openai' ? 'gpt-4o-mini' : 'llama3.1:8b'}
                autoComplete="off"
              />
            </Field>
          </div>

          {/* Ingestion phase card */}
          <div className="space-y-2.5 rounded-md border border-[var(--color-border)] bg-[var(--color-canvas-raised)] px-3 py-2.5">
            <div className="flex items-center gap-1.5 text-[11.5px] font-semibold text-ink">
              <Workflow size={13} className="text-[var(--color-brand)]" />
              Ingestion
              <span className="text-[10px] font-normal text-ink-subtle">
                — classify + plan + generazione pagine
              </span>
            </div>
            <Field label="Vendor" error={errors.provider_ingest_vendor?.message}>
              <select {...register('provider_ingest_vendor')} className="input">
                <option value="ollama">Ollama (locale)</option>
                <option value="openai">OpenAI</option>
              </select>
            </Field>
            <Field
              label="Modello"
              hint={
                ingestVendor === 'openai'
                  ? 'Consigliato modello capace. Es. gpt-4o. Vuoto = eredita default.'
                  : 'Consigliato modello capace. Es. qwen2.5:14b-instruct. Vuoto = eredita default.'
              }
              error={errors.provider_ingest_model?.message}
            >
              <input
                {...register('provider_ingest_model')}
                className="input font-mono text-[11.5px]"
                placeholder={ingestVendor === 'openai' ? 'gpt-4o' : 'qwen2.5:14b-instruct'}
                autoComplete="off"
              />
            </Field>
          </div>

          {isSplit && (
            <div className="rounded-md border border-[var(--color-brand-ring)] bg-[var(--color-brand-soft)] px-3 py-2 text-[10.5px] text-ink-muted">
              Modalità ibrida attiva: chat su <code>{ragVendor}</code>, ingestion su{' '}
              <code>{ingestVendor}</code>. Configura sotto entrambi i provider.
            </div>
          )}

          {/* Shared network credentials */}
          {needsOllama && (
            <Field
              label="Ollama URL"
              hint="Endpoint del servizio Ollama. Predefinito: http://localhost:11434."
              error={errors.provider_ollama_url?.message}
            >
              <input
                {...register('provider_ollama_url')}
                className="input font-mono text-[11.5px]"
                placeholder="http://localhost:11434"
                autoComplete="off"
              />
            </Field>
          )}

          {needsOpenai && (
            <>
              <Field
                label="OpenAI API base"
                hint="Predefinito: https://api.openai.com/v1. Modificalo per Azure / proxy."
                error={errors.provider_openai_api_base?.message}
              >
                <input
                  {...register('provider_openai_api_base')}
                  className="input font-mono text-[11.5px]"
                  placeholder="https://api.openai.com/v1"
                  autoComplete="off"
                />
              </Field>
              <Field
                label="OpenAI API key"
                hint="Conservata in locale. Mai mostrata nelle anteprime."
                error={errors.provider_openai_api_key?.message}
              >
                <input
                  {...register('provider_openai_api_key')}
                  type="password"
                  className="input font-mono text-[11.5px]"
                  placeholder="sk-…"
                  autoComplete="new-password"
                />
              </Field>
            </>
          )}
        </div>
      )}
    </div>
  );
}
