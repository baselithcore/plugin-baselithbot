'use client';

import { useState } from 'react';
import { Copy, RefreshCw } from 'lucide-react';
import { cn } from '@/lib/cn';
import { Avatar, GroundedBadge, IconBtn, type T } from './atoms';

export interface QA {
  q: string;
  a: string;
  grounded: boolean;
  ts: number;
  streaming?: boolean;
}

interface Props {
  qa: QA;
  t: T;
  onRetry: () => void;
  disabled: boolean;
}

export function ChatTurn({ qa, t, onRetry, disabled }: Props) {
  const [copied, setCopied] = useState(false);

  async function copy() {
    await navigator.clipboard.writeText(qa.a);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  return (
    <div className="space-y-2">
      <div className="flex items-start gap-2.5">
        <Avatar tone="user" />
        <div className="flex-1 min-w-0">
          <div className="mb-1 flex items-center gap-2 text-[10px] uppercase tracking-wide text-text-muted">
            <span>{t('youLabel')}</span>
            <span className="font-mono normal-case">
              {new Date(qa.ts).toLocaleTimeString(undefined, {
                hour: '2-digit',
                minute: '2-digit',
              })}
            </span>
          </div>
          <div className="rounded-lg border border-border bg-bg-panel/60 px-3 py-2 text-[12.5px] leading-5 text-text-primary whitespace-pre-wrap">
            {qa.q}
          </div>
        </div>
      </div>

      <div className="flex items-start gap-2.5">
        <Avatar tone="assistant" />
        <div className="flex-1 min-w-0">
          <div className="mb-1 flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 text-[10px] uppercase tracking-wide text-text-muted">
              <span>{t('assistantLabel')}</span>
              {!qa.streaming && <GroundedBadge grounded={qa.grounded} t={t} />}
              {qa.streaming && (
                <span className="inline-flex items-center gap-1 rounded-full border border-status-info/30 bg-status-info/10 px-1.5 py-0.5 text-[9px] font-medium text-status-info normal-case tracking-normal">
                  <span className="h-1.5 w-1.5 rounded-full bg-status-info animate-pulse" />
                  streaming
                </span>
              )}
            </div>
            <div className="flex items-center gap-1">
              <IconBtn
                label={copied ? t('copied') : t('copyAnswer')}
                onClick={copy}
                disabled={qa.streaming}
              >
                <Copy size={11} />
              </IconBtn>
              <IconBtn label={t('retry')} onClick={onRetry} disabled={disabled || qa.streaming}>
                <RefreshCw size={11} />
              </IconBtn>
            </div>
          </div>
          <div
            className={cn(
              'rounded-lg border px-3 py-2.5 text-[12.5px] leading-5 whitespace-pre-wrap',
              qa.streaming
                ? 'border-border bg-bg-canvas text-text-primary'
                : qa.grounded
                  ? 'border-status-info/25 bg-status-info/5 text-text-primary'
                  : 'border-status-warning/30 bg-status-warning/8 text-text-primary'
            )}
          >
            {qa.a}
            {qa.streaming && (
              <span className="ml-0.5 inline-block h-3.5 w-[2px] -mb-0.5 align-middle bg-status-info animate-pulse" />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
