import { Cpu, Eye, EyeOff, KeyRound, Loader2, MessageSquare, Save, Workflow } from 'lucide-react';
import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import { updateProvider } from '../../lib/api/admin';
import { fetchStatus } from '../../lib/api/wiki';
import type { ProviderStatus } from '../../lib/types';
import { Button } from '../ui';

type Vendor = 'ollama' | 'openai';

/**
 * Admin-only provider rotation panel.
 *
 * Two vendor selectors (chat / ingestion) always visible. When they
 * differ → hybrid mode (writes `RAG_VENDOR` / `INGEST_VENDOR` to .env).
 * When equal → single-vendor mode. Network credentials surface only
 * for the vendors actually selected (Ollama URL appears if either
 * phase uses Ollama; OpenAI base+key appear if either uses OpenAI).
 *
 * Wraps `POST /api/admin/provider`. Writes `.env`, mirrors os.environ,
 * refreshes config, resets cached LLM clients — no server restart
 * required. `api_key` fields are write-only; leaving them blank
 * preserves the currently-loaded value.
 */
export function ProviderSection() {
  const [current, setCurrent] = useState<ProviderStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const [ragVendor, setRagVendor] = useState<Vendor>('ollama');
  const [chatModel, setChatModel] = useState('');
  const [ingestVendor, setIngestVendor] = useState<Vendor>('ollama');
  const [ingestModel, setIngestModel] = useState('');

  const [ollamaUrl, setOllamaUrl] = useState('');
  const [openaiBase, setOpenaiBase] = useState('');
  const [openaiKey, setOpenaiKey] = useState('');
  const [showKey, setShowKey] = useState(false);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchStatus()
      .then((s) => {
        if (cancelled) return;
        setCurrent(s.provider);
        setRagVendor(s.provider.rag_vendor);
        setIngestVendor(s.provider.ingest_vendor);
        setChatModel(s.provider.model || '');
        setIngestModel(s.provider.ingest_model || '');
        if (s.provider.rag_vendor === 'ollama' || s.provider.ingest_vendor === 'ollama') {
          setOllamaUrl(
            s.provider.endpoint && s.provider.endpoint.startsWith('http://') ? s.provider.endpoint : ''
          );
        }
        if (s.provider.rag_vendor === 'openai' || s.provider.ingest_vendor === 'openai') {
          setOpenaiBase(
            s.provider.endpoint && s.provider.endpoint.startsWith('https://') ? s.provider.endpoint : ''
          );
        }
      })
      .catch((e: Error) => {
        if (!cancelled) toast.error(`Stato provider: ${e.message}`);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const needsOpenai = ragVendor === 'openai' || ingestVendor === 'openai';
  const needsOllama = ragVendor === 'ollama' || ingestVendor === 'ollama';
  const isSplit = ragVendor !== ingestVendor;

  const handleSave = async () => {
    setBusy(true);
    try {
      const res = await updateProvider({
        vendor: ragVendor,
        rag_vendor: ragVendor,
        ingest_vendor: ingestVendor,
        model: chatModel.trim() || undefined,
        ingest_model: ingestModel.trim() || undefined,
        ollama_url: needsOllama && ollamaUrl.trim() ? ollamaUrl.trim() : undefined,
        openai_api_base: needsOpenai && openaiBase.trim() ? openaiBase.trim() : undefined,
        openai_api_key: needsOpenai && openaiKey ? openaiKey : undefined,
      });
      toast.success(
        res.env_written
          ? 'Provider aggiornato (.env + runtime).'
          : 'Provider aggiornato (runtime — .env non scrivibile).'
      );
      setOpenaiKey('');
      const s = await fetchStatus();
      setCurrent(s.provider);
    } catch (e) {
      toast.error(`Aggiornamento fallito: ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-[11px] text-ink-subtle" role="status">
        <Loader2 size={12} className="animate-spin" aria-hidden /> Controllo dello stato…
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <p className="text-[11px] leading-relaxed text-ink-muted">
        Scegli il vendor indipendentemente per chat e ingestion. Quando differiscono
        viene attivata la modalità ibrida (chat su un provider, ingestion sull'altro).
        Le modifiche vanno in <code>.env</code> e nel processo live — niente restart.
      </p>

      <div className="space-y-3 rounded-md border border-[var(--color-border)] bg-[var(--color-surface)] px-3 py-3">
        <PhaseCard
          icon={MessageSquare}
          title="Chat / RAG"
          subtitle="Usato per generare le risposte."
          vendor={ragVendor}
          onVendor={setRagVendor}
          model={chatModel}
          onModel={setChatModel}
          modelPlaceholder={ragVendor === 'openai' ? 'gpt-4o-mini' : 'llama3.1:8b'}
        />

        <PhaseCard
          icon={Workflow}
          title="Ingestion"
          subtitle="classify + plan + generate."
          vendor={ingestVendor}
          onVendor={setIngestVendor}
          model={ingestModel}
          onModel={setIngestModel}
          modelPlaceholder={ingestVendor === 'openai' ? 'gpt-4o' : 'qwen2.5:14b-instruct'}
        />

        {isSplit && (
          <div className="rounded-md border border-[var(--color-brand-ring)] bg-[var(--color-brand-soft)] px-3 py-2 text-[10.5px] text-ink-muted">
            Modalità ibrida: chat su <code>{ragVendor}</code>, ingestion su{' '}
            <code>{ingestVendor}</code>. Configura entrambi i provider sotto.
          </div>
        )}

        {needsOllama && (
          <Field label="Ollama URL" hint="Endpoint del servizio Ollama.">
            <input
              type="text"
              value={ollamaUrl}
              onChange={(e) => setOllamaUrl(e.target.value)}
              placeholder="http://localhost:11434"
              className="input-text"
            />
          </Field>
        )}

        {needsOpenai && (
          <>
            <Field label="OpenAI API base" hint="Personalizza per Azure / proxy.">
              <input
                type="text"
                value={openaiBase}
                onChange={(e) => setOpenaiBase(e.target.value)}
                placeholder="https://api.openai.com/v1"
                className="input-text"
              />
            </Field>
            <Field
              label="OpenAI API key"
              icon={KeyRound}
              hint="Lascia vuoto per non cambiare la chiave attuale."
            >
              <div className="relative">
                <input
                  type={showKey ? 'text' : 'password'}
                  value={openaiKey}
                  onChange={(e) => setOpenaiKey(e.target.value)}
                  placeholder="sk-proj-…"
                  autoComplete="off"
                  spellCheck={false}
                  className="input-text pr-8"
                />
                <button
                  type="button"
                  onClick={() => setShowKey((v) => !v)}
                  className="absolute right-1 top-1/2 -translate-y-1/2 p-1 text-ink-subtle hover:text-ink"
                  aria-label={showKey ? 'nascondi chiave' : 'mostra chiave'}
                >
                  {showKey ? <EyeOff size={12} /> : <Eye size={12} />}
                </button>
              </div>
            </Field>
          </>
        )}

        <div className="flex items-center justify-between border-t border-[var(--color-border)] pt-2 text-[10px] text-ink-subtle">
          <span>
            Attuale: chat <code>{current?.rag_vendor}</code>/<code>{current?.model}</code>
            {' · ingest '}
            <code>{current?.ingest_vendor}</code>/<code>{current?.ingest_model}</code>
            {current?.split ? ' · split' : ''}
          </span>
          <Button variant="primary" onClick={handleSave} disabled={busy} className="!text-[11px]">
            {busy ? <Loader2 size={11} className="animate-spin" /> : <Save size={11} />}
            Applica
          </Button>
        </div>
      </div>

      <style>{`
        .input-text {
          width: 100%;
          border-radius: 0.375rem;
          border: 1px solid var(--color-border);
          background-color: var(--color-canvas);
          padding: 0.25rem 0.5rem;
          font-size: 11px;
          color: var(--color-ink);
        }
        .input-text:focus { outline: none; box-shadow: 0 0 0 1px var(--color-accent); }
      `}</style>
    </div>
  );
}

function PhaseCard({
  icon: Icon,
  title,
  subtitle,
  vendor,
  onVendor,
  model,
  onModel,
  modelPlaceholder,
}: {
  icon: typeof Cpu;
  title: string;
  subtitle: string;
  vendor: Vendor;
  onVendor: (v: Vendor) => void;
  model: string;
  onModel: (s: string) => void;
  modelPlaceholder: string;
}) {
  return (
    <div className="space-y-2 rounded-md border border-[var(--color-border)] bg-[var(--color-canvas-raised)] px-2.5 py-2.5">
      <div className="flex items-center gap-1.5 text-[11.5px] font-semibold text-ink">
        <Icon size={13} className="text-[var(--color-brand)]" aria-hidden /> {title}
        <span className="text-[10px] font-normal text-ink-subtle">— {subtitle}</span>
      </div>
      <Field label="Vendor" icon={Cpu}>
        <select
          value={vendor}
          onChange={(e) => onVendor(e.target.value as Vendor)}
          className="input-text"
        >
          <option value="ollama">Ollama (locale)</option>
          <option value="openai">OpenAI</option>
        </select>
      </Field>
      <Field label="Modello">
        <input
          type="text"
          value={model}
          onChange={(e) => onModel(e.target.value)}
          placeholder={modelPlaceholder}
          className="input-text"
        />
      </Field>
    </div>
  );
}

function Field({
  label,
  hint,
  icon: Icon,
  children,
}: {
  label: string;
  hint?: string;
  icon?: typeof Cpu;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1">
      <label className="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wide text-ink-subtle">
        {Icon ? <Icon size={11} aria-hidden /> : null}
        {label}
      </label>
      {children}
      {hint ? <p className="text-[10px] leading-snug text-ink-subtle">{hint}</p> : null}
    </div>
  );
}
