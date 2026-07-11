import { motion } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { Loader2, Lock, Send, SlidersHorizontal, Wand2, Zap } from 'lucide-react';
import { isRemoteLlmProvider, type LlmProvider } from '@dbview/shared';
import type { KeyboardEvent, ReactNode, RefObject } from 'react';
import { api } from '../../lib/api.js';
import { cn } from '../../lib/cn.js';
import { ModelCombobox } from './ModelCombobox.js';
import { RemoteModelCombobox } from './RemoteModelCombobox.js';
import type { TurnMode } from './turn-types.js';

const PROVIDERS: { value: LlmProvider; label: string }[] = [
  { value: 'ollama', label: 'Ollama' },
  { value: 'openai', label: 'OpenAI' },
  { value: 'anthropic', label: 'Claude' },
];

const PROVIDER_LABEL: Record<string, string> = {
  ollama: 'Ollama',
  openai: 'OpenAI',
  anthropic: 'Claude',
};

interface QueryComposerProps {
  prompt: string;
  provider: LlmProvider;
  model: string | undefined;
  autoExecute: boolean;
  busy: boolean;
  textareaRef: RefObject<HTMLTextAreaElement | null>;
  onPromptChange: (prompt: string) => void;
  onProviderChange: (provider: LlmProvider) => void;
  onModelChange: (model: string | undefined) => void;
  onAutoExecuteChange: (value: boolean) => void;
  onSend: (mode?: TurnMode) => void;
  onKeyDown: (event: KeyboardEvent<HTMLTextAreaElement>) => void;
}

export function QueryComposer({
  prompt,
  provider,
  model,
  autoExecute,
  busy,
  textareaRef,
  onPromptChange,
  onProviderChange,
  onModelChange,
  onAutoExecuteChange,
  onSend,
  onKeyDown,
}: QueryComposerProps) {
  const canSend = prompt.trim().length > 0 && !busy;
  // Central governance: when the operator has pinned the NL→Query provider,
  // the per-request provider/model are ignored server-side — show a read-only
  // badge instead of the picker so the UI never implies a choice that has none.
  const governance = useQuery({
    queryKey: ['llm-governance'],
    queryFn: () => api.getLlmGovernance(),
    retry: false,
    staleTime: 60_000,
  });
  const enforced = governance.data?.translate;

  return (
    <div
      data-tour="nl2query-composer"
      className="shrink-0 border-t border-border-subtle bg-surface-1/55 p-3"
    >
      <div
        className={cn(
          'rounded-lg border transition-colors',
          'focus-within:border-accent/55 focus-within:ring-1 focus-within:ring-accent/30'
        )}
        style={{
          background:
            'linear-gradient(180deg, rgb(var(--surface-elevated)), rgb(var(--surface-1) / 0.98))',
          borderColor: 'rgb(var(--border-subtle))',
        }}
      >
        <textarea
          ref={textareaRef}
          aria-label={autoExecute ? 'Ask the assistant' : 'Describe a query to draft'}
          className={cn(
            'min-h-[92px] max-h-[220px] w-full resize-none bg-transparent px-3.5 pb-2.5 pt-3.5',
            'text-[13px] leading-[1.55] outline-none placeholder:text-text-dim'
          )}
          placeholder={
            autoExecute
              ? 'Ask about revenue, users, cohorts, anomalies…'
              : 'Describe the query you want drafted…'
          }
          value={prompt}
          onChange={(event) => onPromptChange(event.target.value)}
          onKeyDown={onKeyDown}
          disabled={busy}
        />

        <div className="flex flex-col gap-2 border-t border-border-subtle px-2.5 py-2">
          <div className="flex flex-wrap items-center gap-1.5">
            <div data-tour="nl2query-auto">
              <ModeToggle value={autoExecute} onChange={onAutoExecuteChange} />
            </div>
            <div className="hidden h-5 w-px bg-border-subtle sm:block" />
            <div
              data-tour="nl2query-provider"
              className="flex min-w-0 flex-wrap items-center gap-1.5"
            >
              <span
                className="inline-flex h-7 items-center gap-1.5 rounded-md px-1 text-[11px] text-text-dim"
                aria-hidden="true"
              >
                <SlidersHorizontal className="h-3.5 w-3.5" />
              </span>
              {enforced?.enforced ? (
                <span
                  className="inline-flex h-7 items-center gap-1.5 rounded-md border border-border-subtle px-2 text-[11px] text-text-dim"
                  title="LLM provider is managed centrally by your administrator"
                >
                  <Lock className="h-3 w-3" />
                  {enforced.provider
                    ? (PROVIDER_LABEL[enforced.provider] ?? enforced.provider)
                    : 'Managed'}
                  <span className="text-text-dim/70">· managed</span>
                </span>
              ) : (
                <>
                  <select
                    className="select h-7 text-[12px]"
                    value={provider}
                    onChange={(event) => {
                      onProviderChange(event.target.value as LlmProvider);
                      onModelChange(undefined);
                    }}
                    aria-label="LLM provider"
                    title="LLM provider"
                  >
                    {PROVIDERS.map((p) => (
                      <option key={p.value} value={p.value}>
                        {p.label}
                      </option>
                    ))}
                  </select>
                  {provider === 'ollama' ? (
                    <ModelCombobox
                      value={model}
                      onChange={(value) => onModelChange(value || undefined)}
                    />
                  ) : isRemoteLlmProvider(provider) ? (
                    <RemoteModelCombobox
                      provider={provider}
                      value={model}
                      onChange={(value) => onModelChange(value || undefined)}
                    />
                  ) : null}
                </>
              )}
            </div>
          </div>

          <div className="flex items-center justify-between gap-2">
            <span className="font-mono text-[10px] text-text-dim">
              {prompt.length.toLocaleString()} chars
            </span>
            <button
              type="button"
              onClick={() => onSend()}
              disabled={!canSend}
              className={cn(
                'inline-flex h-9 w-9 items-center justify-center rounded-lg',
                'transition-[background,color,filter,transform] duration-150 ease-[cubic-bezier(0.25,1,0.5,1)]',
                canSend
                  ? 'shadow-md hover:brightness-110 active:translate-y-px active:scale-95'
                  : 'cursor-not-allowed'
              )}
              style={{
                background: canSend
                  ? 'linear-gradient(180deg, rgb(var(--accent)), rgb(var(--accent) / 0.86))'
                  : 'rgb(var(--surface-3))',
                color: canSend ? 'rgb(var(--accent-fg))' : 'rgb(var(--text-dim))',
              }}
              title={autoExecute ? 'Ask' : 'Draft query'}
              aria-label={autoExecute ? 'Ask' : 'Draft query'}
            >
              {busy ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send
                  key={prompt.trim() ? 'on' : 'off'}
                  className={cn('h-4 w-4', canSend && 'send-wake')}
                />
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function ModeToggle({ value, onChange }: { value: boolean; onChange: (value: boolean) => void }) {
  return (
    <div className="segmented" role="group" aria-label="Assistant mode">
      <ModePill active={value} onClick={() => onChange(true)} label="Ask">
        <Zap className="h-3 w-3" />
      </ModePill>
      <ModePill active={!value} onClick={() => onChange(false)} label="Draft">
        <Wand2 className="h-3 w-3" />
      </ModePill>
    </div>
  );
}

function ModePill({
  active,
  onClick,
  label,
  children,
}: {
  active: boolean;
  onClick: () => void;
  label: string;
  children: ReactNode;
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      className={cn('relative h-7 min-w-16 segmented-item', active && 'text-accent')}
      style={active ? { background: 'transparent' } : undefined}
      onClick={onClick}
    >
      {active && (
        <motion.span
          layoutId="nl2-mode-pill"
          className="absolute inset-0 rounded"
          style={{
            background: 'rgb(var(--surface-elevated))',
            boxShadow: '0 1px 3px rgb(var(--shadow-color) / 0.18)',
          }}
          transition={{ duration: 0.26, ease: [0.22, 1, 0.36, 1] }}
        />
      )}
      <span className="relative z-10 inline-flex items-center gap-1.5">
        {children}
        <span>{label}</span>
      </span>
    </button>
  );
}
