import { Clock3, Database, Eraser, PanelRightClose, Sparkles } from 'lucide-react';
import type { UnifiedSchema } from '@dbview/shared';
import { cn } from '../../lib/cn.js';
import { formatSchemaAge, summarizeSchema } from './schema-summary.js';

interface AssistantPanelHeaderProps {
  schema: UnifiedSchema | undefined;
  schemaLoading: boolean;
  conversationCount: number;
  onClear: () => void;
  onCollapse: () => void;
}

export function AssistantPanelHeader({
  schema,
  schemaLoading,
  conversationCount,
  onClear,
  onCollapse,
}: AssistantPanelHeaderProps) {
  const summary = summarizeSchema(schema);
  const schemaAge = formatSchemaAge(schema?.generatedAt);
  const hasConversation = conversationCount > 0;

  return (
    <header className="border-b border-border-subtle bg-surface-1/45 px-3 py-2.5 shrink-0">
      <div className="flex items-start justify-between gap-2">
        <div className="flex min-w-0 items-start gap-2.5">
          <div className="grid h-8 w-8 shrink-0 place-items-center rounded-lg border border-accent/25 bg-accent/10 text-accent shadow-sm shadow-accent/10">
            <Sparkles className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <div className="flex min-w-0 items-center gap-2">
              <h2 className="truncate text-[14px] font-semibold leading-5">Query assistant</h2>
              {hasConversation && (
                <span className="chip h-5 px-1.5 text-[10px]">
                  {conversationCount} {conversationCount === 1 ? 'turn' : 'turns'}
                </span>
              )}
            </div>
            <div className="mt-0.5 flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1 text-[11px] text-text-dim">
              {summary ? (
                <>
                  <span className="inline-flex min-w-0 items-center gap-1 font-medium text-text-muted">
                    <Database className="h-3 w-3 shrink-0 text-accent" />
                    <span className="truncate">{summary.dialect}</span>
                  </span>
                  <span>
                    {summary.primary.value} {summary.primary.label}
                  </span>
                  <span>
                    {summary.secondary.value} {summary.secondary.label}
                  </span>
                  {schemaAge && (
                    <span className="inline-flex items-center gap-1">
                      <Clock3 className="h-3 w-3" />
                      {schemaAge}
                    </span>
                  )}
                </>
              ) : (
                <span className={cn(schemaLoading && 'animate-pulse')}>
                  {schemaLoading ? 'Schema loading' : 'Schema unavailable'}
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-1">
          {hasConversation && (
            <button
              type="button"
              onClick={onClear}
              className="btn-ghost h-8 w-8 p-0"
              aria-label="Clear conversation"
              title="Clear conversation"
            >
              <Eraser className="h-3.5 w-3.5" />
            </button>
          )}
          <button
            type="button"
            onClick={onCollapse}
            className="btn-ghost h-8 w-8 p-0"
            aria-label="Collapse panel"
            title="Collapse panel"
          >
            <PanelRightClose className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>
    </header>
  );
}
