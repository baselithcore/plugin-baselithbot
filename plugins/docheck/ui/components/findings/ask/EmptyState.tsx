'use client';

import { Sparkles } from 'lucide-react';
import type { T } from './atoms';

interface Props {
  t: T;
  suggestions: string[];
  onPick: (s: string) => void;
  disabled: boolean;
}

export function EmptyState({ t, suggestions, onPick, disabled }: Props) {
  return (
    <div className="space-y-3">
      <div className="rounded-lg border border-dashed border-border bg-bg-canvas/60 p-4">
        <div className="flex items-start gap-2.5">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-status-info/10 text-status-info">
            <Sparkles size={14} />
          </div>
          <div className="min-w-0">
            <div className="text-[12px] font-medium text-text-primary">{t('introTitle')}</div>
            <p className="mt-1 text-[12px] leading-5 text-text-muted">{t('intro')}</p>
          </div>
        </div>
      </div>
      <div>
        <div className="mb-2 px-1 text-[10px] font-semibold uppercase tracking-wide text-text-muted">
          {t('suggestionsLabel')}
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {suggestions.map((s) => (
            <button
              key={s}
              type="button"
              disabled={disabled}
              onClick={() => onPick(s)}
              className="text-left rounded-md border border-border bg-bg-canvas hover:bg-bg-panel-elev hover:border-border-strong px-3 py-2 text-[12px] leading-5 text-text-secondary hover:text-text-primary transition-colors ring-focus disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {s}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
