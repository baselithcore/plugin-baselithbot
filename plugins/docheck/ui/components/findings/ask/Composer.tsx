'use client';

import { forwardRef } from 'react';
import { CornerDownLeft, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/cn';
import type { T } from './atoms';

export interface ComposerProps {
  value: string;
  onChange: (v: string) => void;
  onSubmit: () => void;
  busy: boolean;
  canSubmit: boolean;
  charCount: number;
  overLimit: boolean;
  maxChars: number;
  disabled: boolean;
  historyCount: number;
  onClearChat: () => void;
  t: T;
}

export const Composer = forwardRef<HTMLTextAreaElement, ComposerProps>(
  function Composer(props, ref) {
    const {
      value,
      onChange,
      onSubmit,
      busy,
      canSubmit,
      charCount,
      overLimit,
      maxChars,
      disabled,
      historyCount,
      onClearChat,
      t,
    } = props;
    return (
      <footer className="border-t border-border bg-bg-panel/95 backdrop-blur-md p-3 space-y-2">
        <div
          className={cn(
            'rounded-lg border bg-bg-canvas transition-colors focus-within:border-status-info/50',
            overLimit ? 'border-status-danger/50' : 'border-border'
          )}
        >
          <textarea
            ref={ref}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) {
                e.preventDefault();
                onSubmit();
              }
            }}
            rows={2}
            disabled={busy || disabled}
            placeholder={t('placeholder')}
            className="block w-full min-h-[56px] max-h-[180px] resize-none bg-transparent px-3 py-2.5 text-[13px] leading-5 outline-none placeholder:text-text-muted disabled:opacity-60"
          />
          <div className="flex items-center justify-between gap-2 px-2 pb-2 pt-0">
            <div className="flex items-center gap-2">
              {historyCount > 0 && (
                <button
                  type="button"
                  onClick={onClearChat}
                  disabled={busy}
                  className="inline-flex h-7 items-center gap-1.5 rounded-md border border-border bg-bg-canvas px-2 text-[10.5px] text-text-muted hover:text-text-primary hover:bg-bg-panel-elev transition-colors ring-focus disabled:opacity-50"
                  title={t('clearChat')}
                >
                  <Trash2 size={11} /> {t('clearChat')}
                </button>
              )}
              <span
                className={cn(
                  'text-[10px] font-mono',
                  overLimit ? 'text-status-danger' : 'text-text-muted'
                )}
              >
                {charCount}/{maxChars}
              </span>
            </div>
            <Button size="sm" onClick={onSubmit} disabled={!canSubmit} className="gap-1.5">
              <span>{t('send')}</span>
              <kbd className="hidden sm:inline-flex items-center gap-0.5 rounded border border-white/20 bg-white/10 px-1 py-px text-[9px] font-mono">
                ⌘<CornerDownLeft size={9} />
              </kbd>
            </Button>
          </div>
        </div>
        <div className="flex items-center justify-between text-[10px] text-text-muted">
          <span>{t('kbdHint')}</span>
          <span className="hidden sm:inline">{t('groundedDisclaimer')}</span>
        </div>
      </footer>
    );
  }
);
