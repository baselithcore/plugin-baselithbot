import { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import * as Popover from '@radix-ui/react-popover';
import { Command } from 'cmdk';
import { AnimatePresence, motion } from 'framer-motion';
import {
  AlertTriangle,
  Check,
  ChevronsUpDown,
  Cpu,
  Loader2,
  RefreshCw,
  Sparkles,
  X,
} from 'lucide-react';
import { isCodingOllamaModel, type OllamaModel } from '@dbview/shared';
import { api } from '../../lib/api.js';
import { cn } from '../../lib/cn.js';

interface ModelComboboxProps {
  value: string | undefined;
  onChange: (model: string | undefined) => void;
}

/**
 * Modern combobox for selecting an Ollama coding model.
 *
 * UX rules followed:
 *   - Filterable input as the primary affordance (typeahead > scroll).
 *   - Keyboard nav (arrow/enter/esc) via cmdk; focus returns on close.
 *   - Coding-only filter applied at source; toggle to widen if user needs.
 *   - Distinct loading / error / empty / unreachable states.
 *   - Visible selection + one-click clear (returns to "auto").
 *   - Compact trigger fits in panel header alongside provider select.
 */
export function ModelCombobox({ value, onChange }: ModelComboboxProps) {
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState('');
  const [showAll, setShowAll] = useState(false);

  const models = useQuery({
    queryKey: ['ollama-models'],
    queryFn: () => api.listOllamaModels(),
    retry: false,
    staleTime: 30_000,
  });

  const { coding, hiddenCount } = useMemo(() => {
    const all = models.data?.models ?? [];
    const codingList = all.filter((m) => isCodingOllamaModel(m.name));
    return {
      coding: codingList,
      hiddenCount: Math.max(0, all.length - codingList.length),
    };
  }, [models.data]);

  const visible = useMemo(
    () => (showAll ? (models.data?.models ?? []) : coding),
    [showAll, models.data?.models, coding],
  );
  const grouped = useMemo(() => groupByFamily(visible), [visible]);

  const select = (name: string) => {
    onChange(name);
    setOpen(false);
    setSearch('');
  };

  const clear = (e: React.MouseEvent) => {
    e.stopPropagation();
    onChange(undefined);
  };

  // Cross-component trigger: AssistantTurnError fires this when a turn fails
  // with "model not found" / unsafe SQL, so the user can pick a different
  // model without hunting for the dropdown.
  useEffect(() => {
    const open = () => setOpen(true);
    window.addEventListener('dbview:open-model-picker', open);
    return () => window.removeEventListener('dbview:open-model-picker', open);
  }, []);

  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <button
          type="button"
          aria-label="Select model"
          className={cn(
            'group inline-flex items-center gap-1.5 h-7 px-2 rounded-md border text-[12px] font-mono',
            'transition-colors min-w-[132px] max-w-[190px]',
            'bg-surface-2/60 border-border-subtle hover:bg-surface-3/70 hover:border-accent/40',
            open && 'border-accent/60 ring-1 ring-accent/40',
          )}
          title={value ? `Model: ${value}` : 'Auto-select coding model'}
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
                className="w-[340px] rounded-lg border shadow-2xl overflow-hidden"
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
                      placeholder="Search models…"
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

                  <Command.List className="max-h-[300px] overflow-auto p-1.5">
                    {models.isLoading ? (
                      <div className="flex items-center gap-2 px-3 py-6 text-[12px] text-text-dim">
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        Loading models…
                      </div>
                    ) : models.error ? (
                      <UnreachableState message={(models.error as Error).message} />
                    ) : visible.length === 0 ? (
                      <EmptyState
                        hiddenCount={hiddenCount}
                        showAll={showAll}
                        onToggle={() => setShowAll(true)}
                      />
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
                              Use server default for this dialect
                            </div>
                          </div>
                          {!value && <Check className="w-3.5 h-3.5 text-accent" />}
                        </Command.Item>
                        {Object.entries(grouped).map(([family, items]) => (
                          <Command.Group
                            key={family}
                            heading={family}
                            className="text-[10px] uppercase tracking-wider text-text-dim px-2 pt-2 pb-1"
                          >
                            {items.map((m) => (
                              <ModelRow
                                key={m.name}
                                model={m}
                                selected={m.name === value}
                                onSelect={() => select(m.name)}
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
                      {visible.length} {showAll ? 'total' : 'coding'} · {hiddenCount} hidden
                    </span>
                    {hiddenCount > 0 && (
                      <button
                        type="button"
                        onClick={() => setShowAll((v) => !v)}
                        className="text-accent hover:underline"
                      >
                        {showAll ? 'Coding only' : 'Show all'}
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
  model: OllamaModel;
  selected: boolean;
  onSelect: () => void;
}) {
  const coding = isCodingOllamaModel(model.name);
  return (
    <Command.Item
      value={`${model.name} ${model.family ?? ''} ${model.parameterSize ?? ''}`}
      onSelect={onSelect}
      className="flex items-center gap-2 px-2.5 py-1.5 rounded-md cursor-pointer data-[selected=true]:bg-surface-2"
    >
      <span
        className={cn(
          'w-1.5 h-1.5 rounded-full shrink-0',
          coding ? 'bg-emerald-400' : 'bg-amber-400/70',
        )}
        title={coding ? 'Coding model' : 'Not classified as coding model'}
      />
      <span className="flex-1 truncate text-[12px] font-mono">{model.name}</span>
      {model.parameterSize && (
        <span className="chip h-5 text-[10px] px-1.5">{model.parameterSize}</span>
      )}
      {selected && <Check className="w-3.5 h-3.5 text-accent" />}
    </Command.Item>
  );
}

function UnreachableState({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-start gap-1 px-3 py-4 text-[12px]">
      <div className="flex items-center gap-1.5 text-amber-400">
        <AlertTriangle className="w-3.5 h-3.5" />
        <span className="font-medium">Ollama unreachable</span>
      </div>
      <p className="text-text-dim">
        Verify <code className="font-mono">OLLAMA_BASE_URL</code> is set in the API environment and
        that <code className="font-mono">ollama serve</code> is running.
      </p>
      <p className="text-text-dim font-mono text-[10px] break-all">{message}</p>
    </div>
  );
}

function EmptyState({
  hiddenCount,
  showAll,
  onToggle,
}: {
  hiddenCount: number;
  showAll: boolean;
  onToggle: () => void;
}) {
  return (
    <div className="flex flex-col items-start gap-1.5 px-3 py-5 text-[12px]">
      <div className="font-medium text-text">No coding-tuned models installed.</div>
      <p className="text-text-dim">
        Pull one with e.g. <code className="font-mono text-text">ollama pull codellama:7b</code> or{' '}
        <code className="font-mono text-text">ollama pull sqlcoder:7b</code>.
      </p>
      {hiddenCount > 0 && !showAll && (
        <button
          type="button"
          onClick={onToggle}
          className="text-accent hover:underline text-[11px]"
        >
          Show all {hiddenCount} installed models
        </button>
      )}
    </div>
  );
}

function groupByFamily(models: OllamaModel[]): Record<string, OllamaModel[]> {
  const out: Record<string, OllamaModel[]> = {};
  for (const m of models) {
    const family = deriveFamily(m);
    (out[family] ??= []).push(m);
  }
  for (const list of Object.values(out)) {
    list.sort((a, b) => a.name.localeCompare(b.name));
  }
  return out;
}

function deriveFamily(m: OllamaModel): string {
  if (m.family) return m.family;
  const base = m.name.split(':')[0] ?? m.name;
  return base.split(/[-_/]/)[0] ?? base;
}
