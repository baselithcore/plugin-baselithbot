import { motion } from 'framer-motion';
import { ArrowRight, Database, Sparkles } from 'lucide-react';
import type { UnifiedSchema } from '@dbview/shared';
import { summarizeSchema } from './schema-summary.js';

interface SuggestionsViewProps {
  onPick: (suggestion: string) => void;
  suggestions: string[];
  schema: UnifiedSchema | undefined;
  schemaLoading: boolean;
}

export function SuggestionsView({
  onPick,
  suggestions,
  schema,
  schemaLoading,
}: SuggestionsViewProps) {
  const summary = summarizeSchema(schema);

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] }}
      className="flex h-full min-h-[360px] flex-col justify-center gap-4"
    >
      <div className="mx-auto flex max-w-[420px] flex-col items-center gap-3 text-center">
        <div className="grid h-11 w-11 place-items-center rounded-lg border border-accent/25 bg-accent/10 text-accent shadow-sm shadow-accent/10">
          <Sparkles className="h-5 w-5" />
        </div>
        <div className="space-y-1">
          <div className="text-[15px] font-semibold">Schema prompts</div>
          <div className="flex flex-wrap items-center justify-center gap-1.5 text-[11px] text-text-dim">
            {summary ? (
              <>
                <span className="inline-flex items-center gap-1 rounded-md border border-border-subtle bg-surface-2/55 px-2 py-1 text-text-muted">
                  <Database className="h-3 w-3 text-accent" />
                  {summary.dialect}
                </span>
                <span className="rounded-md border border-border-subtle bg-surface-2/45 px-2 py-1">
                  {summary.primary.value} {summary.primary.label}
                </span>
                <span className="rounded-md border border-border-subtle bg-surface-2/45 px-2 py-1">
                  {summary.secondary.value} {summary.secondary.label}
                </span>
              </>
            ) : (
              <span className={schemaLoading ? 'animate-pulse' : undefined}>
                {schemaLoading ? 'Schema loading' : 'Schema unavailable'}
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="grid gap-2">
        {suggestions.map((suggestion, index) => (
          <button
            key={suggestion}
            type="button"
            onClick={() => onPick(suggestion)}
            className="group flex min-h-12 items-center gap-3 rounded-lg border border-border-subtle bg-surface-2/35 px-3 py-2.5 text-left transition-colors hover:border-accent/45 hover:bg-surface-2/70"
          >
            <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-surface-3/60 font-mono text-[10px] text-text-dim group-hover:text-accent">
              {index + 1}
            </span>
            <span className="min-w-0 flex-1 text-[13px] leading-5 text-text">{suggestion}</span>
            <ArrowRight className="h-3.5 w-3.5 shrink-0 text-text-dim transition-transform group-hover:translate-x-0.5 group-hover:text-accent" />
          </button>
        ))}
      </div>
    </motion.div>
  );
}
