import { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertTriangle,
  CheckCircle2,
  Eye,
  EyeOff,
  KeyRound,
  Loader2,
  Lock,
  Trash2,
} from 'lucide-react';
import { toast } from 'sonner';
import type { RemoteLlmProvider } from '@dbview/shared';
import { api } from '../../lib/api.js';
import { cn } from '../../lib/cn.js';

const PROVIDERS: {
  id: RemoteLlmProvider;
  label: string;
  signupUrl: string;
  placeholder: string;
}[] = [
  {
    id: 'openai',
    label: 'OpenAI',
    signupUrl: 'https://platform.openai.com/api-keys',
    placeholder: 'sk-…',
  },
  {
    id: 'anthropic',
    label: 'Anthropic',
    signupUrl: 'https://console.anthropic.com/settings/keys',
    placeholder: 'sk-ant-…',
  },
];

/**
 * Per-user API-key management + provider model browser.
 *
 * Pattern:
 *   - Key is masked when stored (server returns only last 4 chars).
 *   - "Test" hits the provider's `/models` endpoint; cheap, no token cost.
 *   - "Models" list reloads after a successful save so the user can pick
 *     from the live catalogue rather than guessing model ids.
 */
export function AiProvidersSection() {
  const governance = useQuery({
    queryKey: ['llm-governance'],
    queryFn: () => api.getLlmGovernance(),
    retry: false,
    staleTime: 60_000,
  });

  // When the host operator has centrally pinned the LLM provider, per-user
  // keys are ignored server-side — hide the BYOK controls and explain why.
  if (governance.data?.enforced) {
    return <GovernedNotice provider={governance.data.translate.provider} />;
  }

  return (
    <div className="flex flex-col gap-3">
      {PROVIDERS.map((p) => (
        <ProviderCard key={p.id} provider={p} />
      ))}
    </div>
  );
}

function GovernedNotice({ provider }: { provider: string | null }) {
  return (
    <div
      className="flex items-start gap-2.5 rounded-lg border p-3"
      style={{
        background: 'rgb(var(--surface-2) / 0.4)',
        borderColor: 'rgb(var(--border-subtle))',
      }}
    >
      <Lock className="mt-0.5 h-3.5 w-3.5 shrink-0 text-text-dim" />
      <div className="flex flex-col gap-1">
        <span className="text-[13px] font-medium">LLM managed centrally</span>
        <p className="text-[11px] leading-relaxed text-text-dim">
          The LLM provider{provider ? ` (${provider})` : ''} and model for this workspace are set by
          your administrator in the platform console. Per-user API keys are not used here.
        </p>
      </div>
    </div>
  );
}

function ProviderCard({
  provider,
}: {
  provider: { id: RemoteLlmProvider; label: string; signupUrl: string; placeholder: string };
}) {
  const qc = useQueryClient();
  const credentialKey = ['llm-credential', provider.id] as const;
  const modelsKey = ['remote-models', provider.id] as const;

  const status = useQuery({
    queryKey: credentialKey,
    queryFn: () => api.getLlmCredential(provider.id),
    retry: false,
    staleTime: 30_000,
  });

  const [draft, setDraft] = useState('');
  const [reveal, setReveal] = useState(false);

  const save = useMutation({
    mutationFn: (apiKey: string) => api.setLlmCredential(provider.id, { apiKey }),
    onSuccess: (next) => {
      qc.setQueryData(credentialKey, next);
      void qc.invalidateQueries({ queryKey: modelsKey });
      setDraft('');
      toast.success(`${provider.label} key saved`);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const remove = useMutation({
    mutationFn: () => api.deleteLlmCredential(provider.id),
    onSuccess: (next) => {
      qc.setQueryData(credentialKey, next);
      void qc.invalidateQueries({ queryKey: modelsKey });
      toast.success(`${provider.label} key removed`);
    },
    onError: (err: Error) => toast.error(err.message),
  });

  const test = useMutation({
    mutationFn: (override?: string) =>
      api.testLlmCredential(provider.id, override ? { apiKey: override } : {}),
    onSuccess: (r) => toast.success(`OK — ${r.modelCount} models, ${r.latencyMs} ms`),
    onError: (err: Error) => toast.error(err.message),
  });

  const hasKey = status.data?.hasKey === true;
  const envFallback = status.data?.envFallback === true;

  return (
    <div
      className="flex flex-col gap-3 rounded-lg border p-3"
      style={{
        background: 'rgb(var(--surface-2) / 0.4)',
        borderColor: 'rgb(var(--border-subtle))',
      }}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <KeyRound className="w-3.5 h-3.5 text-text-dim" />
          <span className="text-[13px] font-medium">{provider.label}</span>
          {hasKey && !envFallback && (
            <span className="chip h-5 text-[10px] px-1.5 border-emerald-500/30 text-emerald-300">
              key saved
            </span>
          )}
          {envFallback && (
            <span className="chip h-5 text-[10px] px-1.5 border-amber-500/30 text-amber-300">
              env fallback
            </span>
          )}
        </div>
        <a
          href={provider.signupUrl}
          target="_blank"
          rel="noreferrer noopener"
          className="text-[11px] text-text-dim hover:text-accent"
        >
          get key ↗
        </a>
      </div>

      <div className="flex flex-col gap-2">
        <div className="relative">
          <input
            type={reveal ? 'text' : 'password'}
            className="input pr-10 font-mono text-[12px]"
            placeholder={
              status.data?.maskedTail ? `current: ${status.data.maskedTail}` : provider.placeholder
            }
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            autoComplete="off"
            spellCheck={false}
          />
          <button
            type="button"
            className="absolute right-2 top-1/2 -translate-y-1/2 btn-icon w-7 h-7"
            onClick={() => setReveal((v) => !v)}
            aria-label={reveal ? 'Hide' : 'Reveal'}
          >
            {reveal ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            disabled={!draft.trim() || save.isPending}
            onClick={() => save.mutate(draft.trim())}
            className={cn('btn-primary h-8 text-[12px]', !draft.trim() && 'opacity-50')}
          >
            {save.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : 'Save'}
          </button>
          <button
            type="button"
            disabled={test.isPending || (!draft.trim() && !hasKey)}
            onClick={() => test.mutate(draft.trim() || undefined)}
            className="btn h-8 text-[12px]"
            title={draft.trim() ? 'Test the typed key without saving' : 'Test the saved key'}
          >
            {test.isPending ? (
              <Loader2 className="w-3 h-3 animate-spin" />
            ) : (
              <span className="inline-flex items-center gap-1">
                <CheckCircle2 className="w-3 h-3" />
                Test
              </span>
            )}
          </button>
          {hasKey && !envFallback && (
            <button
              type="button"
              disabled={remove.isPending}
              onClick={() => remove.mutate()}
              className="btn h-8 text-[12px] text-rose-300 hover:text-rose-200"
              title="Remove saved key"
            >
              {remove.isPending ? (
                <Loader2 className="w-3 h-3 animate-spin" />
              ) : (
                <span className="inline-flex items-center gap-1">
                  <Trash2 className="w-3 h-3" />
                  Remove
                </span>
              )}
            </button>
          )}
        </div>

        {test.isError && (
          <div className="flex items-start gap-1.5 text-[11px] text-amber-300">
            <AlertTriangle className="w-3 h-3 mt-0.5 shrink-0" />
            <span className="break-all">{(test.error as Error).message}</span>
          </div>
        )}
      </div>

      {hasKey && <ProviderModels provider={provider.id} label={provider.label} />}
    </div>
  );
}

function ProviderModels({ provider, label }: { provider: RemoteLlmProvider; label: string }) {
  const [expanded, setExpanded] = useState(false);
  const models = useQuery({
    queryKey: ['remote-models', provider],
    queryFn: () => api.listRemoteModels(provider),
    enabled: expanded,
    retry: false,
    staleTime: 60_000,
  });

  return (
    <div className="flex flex-col gap-1.5">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="text-[11px] text-accent hover:underline self-start"
      >
        {expanded ? 'Hide' : 'Browse'} {label} models
      </button>
      {expanded && (
        <div
          className="rounded border p-2 max-h-[180px] overflow-auto"
          style={{
            background: 'rgb(var(--surface-1) / 0.6)',
            borderColor: 'rgb(var(--border-subtle))',
          }}
        >
          {models.isLoading ? (
            <div className="flex items-center gap-1.5 text-[11px] text-text-dim">
              <Loader2 className="w-3 h-3 animate-spin" />
              Loading…
            </div>
          ) : models.error ? (
            <div className="text-[11px] text-amber-300 break-all">
              {(models.error as Error).message}
            </div>
          ) : models.data && models.data.models.length > 0 ? (
            <ul className="grid gap-0.5">
              {models.data.models.map((m) => (
                <li key={m.id} className="text-[11px] font-mono text-text-muted truncate">
                  {m.id}
                  {m.displayName && m.displayName !== m.id && (
                    <span className="text-text-dim"> — {m.displayName}</span>
                  )}
                </li>
              ))}
            </ul>
          ) : (
            <div className="text-[11px] text-text-dim">No models returned.</div>
          )}
        </div>
      )}
    </div>
  );
}
