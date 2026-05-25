import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import * as Popover from '@radix-ui/react-popover';
import { Command } from 'cmdk';
import { AnimatePresence, motion } from 'framer-motion';
import {
  AlertTriangle,
  Check,
  ChevronsUpDown,
  Cpu,
  KeyRound,
  Loader2,
  RefreshCw,
  Sparkles,
  X,
} from 'lucide-react';
import type { RemoteLlmProvider, RemoteModel } from '@dbview/shared';
import { api } from '../../lib/api.js';
import { cn } from '../../lib/cn.js';

/**
 * NL2SQL-relevant model family prefix → display order.
 * Anything that doesn't match falls into "other" at the bottom.
 *
 * Embedding / image / audio models are filtered out by default: they cannot
 * generate SQL and only clutter the picker. The user can still type any
 * value manually; this picker just promotes the useful candidates.
 */
const FAMILY_ORDER: Record<RemoteLlmProvider, string[]> = {
  openai: ['gpt-4o', 'o1', 'o3', 'gpt-4', 'gpt-3.5'],
  anthropic: ['claude-opus', 'claude-sonnet', 'claude-haiku', 'claude'],
};

const UNUSABLE_FAMILIES = new Set(['embeddings', 'audio', 'image']);

interface Props {
  provider: RemoteLlmProvider;
  value: string | undefined;
  onChange: (model: string | undefined) => void;
}

export function RemoteModelCombobox({ provider, value, onChange }: Props) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [showAll, setShowAll] = useState(false);

  const models = useQuery({
    queryKey: ['remote-models', provider],
    queryFn: () => api.listRemoteModels(provider),
    retry: false,
    staleTime: 60_000,
  });

  const { usable, hiddenCount } = useMemo(() => {
    const all = models.data?.models ?? [];
    const filtered = all.filter((m) => !UNUSABLE_FAMILIES.has(m.family ?? ''));
    return { usable: filtered, hiddenCount: Math.max(0, all.length - filtered.length) };
  }, [models.data]);

  const visible = useMemo(
    () => (showAll ? (models.data?.models ?? []) : usable),
    [showAll, models.data?.models, usable],
  );
  const grouped = useMemo(() => groupByFamily(visible, provider), [visible, provider]);

  const errorMessage = (models.error as Error | null)?.message ?? '';
  const missingKey = /missing_api_key/i.test(errorMessage) || errorMessage.includes('No API key');

  const select = (id: string) => {
    onChange(id);
    setOpen(false);
    setSearch('');
  };

  const clear = (e: React.MouseEvent) => {
    e.stopPropagation();
    onChange(undefined);
  };

  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <button
          type="button"
          aria-label="Select model"
          className={cn(
            'group inline-flex items-center gap-1.5 h-7 px-2 rounded-md border text-[12px] font-mono',
            'transition-colors min-w-[160px] max-w-[230px]',
            'bg-surface-2/60 border-border-subtle hover:bg-surface-3/70 hover:border-accent/40',
            open && 'border-accent/60 ring-1 ring-accent/40',
          )}
          title={value ? `Model: ${value}` : 'Auto-select default model'}
        >
          <Cpu className="w-3.5 h-3.5 shrink-0 text-text-muted group-hover:text-accent" />
          <span className={cn('flex-1 truncate text-left', !value && 'text-text-dim italic')}>
            {models.isLoading && !value ? 'loading…' : value || 'auto'}
          </span>
          {value ? (
            <span
              role="button"
              aria-label="Clear model"
              tabIndex={-1}
              onClick={clear}
              className="inline-flex items-center justify-center w-4 h-4 rounded hover:bg-surface-3 text-text-dim hover:text-text"
            >
              <X className="w-3 h-3" />
            </span>
          ) : (
            <ChevronsUpDown className="w-3 h-3 text-text-dim" />
          )}
        </button>
      </Popover.Trigger>
      <AnimatePresence>
        {open && (
          <Popover.Portal forceMount>
            <Popover.Content align="end" sideOffset={6} className="z-50 outline-none" asChild>
              <motion.div
                initial={{ opacity: 0, y: -4, scale: 0.98 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: -2, scale: 0.99 }}
                transition={{ duration: 0.14, ease: [0.22, 1, 0.36, 1] }}
                className="w-[360px] rounded-lg border shadow-2xl overflow-hidden"
                style={{
                  background:
                    'linear-gradient(180deg, rgb(var(--surface-elevated)), rgb(var(--surface-1)))',
                  borderColor: 'rgb(var(--border-subtle))',
                }}
              >
                <Command className="flex flex-col" loop shouldFilter>
                  <div
                    className="flex items-center gap-2 px-2.5 h-10 border-b"
                    style={{ borderColor: 'rgb(var(--border-subtle))' }}
                  >
                    <Sparkles className="w-3.5 h-3.5 text-text-muted shrink-0" />
                    <Command.Input
                      autoFocus
                      placeholder={`Search ${provider} models…`}
                      value={search}
                      onValueChange={setSearch}
                      className="flex-1 bg-transparent outline-none text-[13px] placeholder:text-text-dim"
                    />
                    <button
                      type="button"
                      onClick={() => models.refetch()}
                      title="Refresh"
                      className="btn-icon w-6 h-6"
                    >
                      {models.isFetching ? (
                        <Loader2 className="w-3 h-3 animate-spin" />
                      ) : (
                        <RefreshCw className="w-3 h-3" />
                      )}
                    </button>
                  </div>

                  <Command.List className="max-h-[320px] overflow-auto p-1.5">
                    {models.isLoading ? (
                      <div className="flex items-center gap-2 px-3 py-6 text-[12px] text-text-dim">
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        Loading models…
                      </div>
                    ) : models.error ? (
                      missingKey ? (
                        <MissingKeyState provider={provider} />
                      ) : (
                        <ErrorState message={errorMessage} />
                      )
                    ) : visible.length === 0 ? (
                      <EmptyState />
                    ) : (
                      <>
                        <Command.Empty className="px-3 py-6 text-center text-[12px] text-text-dim">
                          No matches.
                        </Command.Empty>
                        <Command.Item
                          value="auto __auto__"
                          onSelect={() => select('')}
                          className="flex items-center gap-2 px-2.5 py-2 rounded-md cursor-pointer data-[selected=true]:bg-surface-2"
                        >
                          <Sparkles className="w-3.5 h-3.5 text-accent" />
                          <div className="flex-1">
                            <div className="text-[13px]">Auto</div>
                            <div className="text-[10px] text-text-dim">
                              Use server default for this provider
                            </div>
                          </div>
                          {!value && <Check className="w-3.5 h-3.5 text-accent" />}
                        </Command.Item>
                        {grouped.map(([family, items]) => (
                          <Command.Group
                            key={family}
                            heading={family}
                            className="text-[10px] uppercase tracking-wider text-text-dim px-2 pt-2 pb-1"
                          >
                            {items.map((m) => (
                              <ModelRow
                                key={m.id}
                                model={m}
                                selected={m.id === value}
                                onSelect={() => select(m.id)}
                              />
                            ))}
                          </Command.Group>
                        ))}
                      </>
                    )}
                  </Command.List>

                  <div
                    className="flex items-center justify-between gap-2 px-2.5 h-9 border-t text-[10px] text-text-dim"
                    style={{ borderColor: 'rgb(var(--border-subtle))' }}
                  >
                    <span className="font-mono">
                      {visible.length} {showAll ? 'total' : 'usable'} · {hiddenCount} hidden
                    </span>
                    {hiddenCount > 0 && (
                      <button
                        type="button"
                        onClick={() => setShowAll((v) => !v)}
                        className="text-accent hover:underline"
                      >
                        {showAll ? 'Usable only' : 'Show all'}
                      </button>
                    )}
                  </div>
                </Command>
              </motion.div>
            </Popover.Content>
          </Popover.Portal>
        )}
      </AnimatePresence>
    </Popover.Root>
  );
}

function ModelRow({
  model,
  selected,
  onSelect,
}: {
  model: RemoteModel;
  selected: boolean;
  onSelect: () => void;
}) {
  const isUnusable = UNUSABLE_FAMILIES.has(model.family ?? '');
  return (
    <Command.Item
      value={`${model.id} ${model.displayName ?? ''} ${model.family ?? ''}`}
      onSelect={onSelect}
      className="flex items-center gap-2 px-2.5 py-1.5 rounded-md cursor-pointer data-[selected=true]:bg-surface-2"
    >
      <span
        className={cn(
          'w-1.5 h-1.5 rounded-full shrink-0',
          isUnusable ? 'bg-amber-400/70' : 'bg-emerald-400',
        )}
        title={isUnusable ? 'Not a chat model' : 'Chat model'}
      />
      <span className="flex-1 truncate text-[12px] font-mono">{model.id}</span>
      {selected && <Check className="w-3.5 h-3.5 text-accent" />}
    </Command.Item>
  );
}

function MissingKeyState({ provider }: { provider: RemoteLlmProvider }) {
  return (
    <div className="flex flex-col items-start gap-1 px-3 py-4 text-[12px]">
      <div className="flex items-center gap-1.5 text-amber-400">
        <KeyRound className="w-3.5 h-3.5" />
        <span className="font-medium">No {provider} API key</span>
      </div>
      <p className="text-text-dim">
        Open <span className="font-medium">Settings → AI Providers</span> to save a key, then
        re-open the model picker.
      </p>
    </div>
  );
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-start gap-1 px-3 py-4 text-[12px]">
      <div className="flex items-center gap-1.5 text-amber-400">
        <AlertTriangle className="w-3.5 h-3.5" />
        <span className="font-medium">Provider unreachable</span>
      </div>
      <p className="text-text-dim font-mono text-[10px] break-all">{message}</p>
    </div>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-start gap-1.5 px-3 py-5 text-[12px] text-text-dim">
      No models returned by the provider for this key.
    </div>
  );
}

/**
 * Group + sort models. Families known to be NL2SQL-relevant come first in
 * the configured order; everything else is grouped under "other".
 */
function groupByFamily(
  models: RemoteModel[],
  provider: RemoteLlmProvider,
): [string, RemoteModel[]][] {
  const order = FAMILY_ORDER[provider];
  const buckets: Record<string, RemoteModel[]> = {};
  for (const m of models) {
    const family = m.family ?? 'other';
    (buckets[family] ??= []).push(m);
  }
  for (const list of Object.values(buckets)) {
    list.sort((a, b) => a.id.localeCompare(b.id));
  }
  const ranked: [string, RemoteModel[]][] = [];
  const seen = new Set<string>();
  for (const fam of order) {
    if (buckets[fam]) {
      ranked.push([fam, buckets[fam]]);
      seen.add(fam);
    }
  }
  for (const [fam, list] of Object.entries(buckets)) {
    if (!seen.has(fam)) ranked.push([fam, list]);
  }
  return ranked;
}
