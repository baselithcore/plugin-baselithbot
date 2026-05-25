'use client';

import { useEffect, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';
import { Sparkles, Link as LinkIcon, FileText } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { cn } from '@/lib/cn';
import type { SuggestedRule } from '@/lib/api/policies';

type SuggestMode = 'url' | 'file';

/**
 * ADR-0015: incremental rule discovery against an existing policy.
 *
 * Two-stage flow inside one modal:
 *  1. operator pastes a URL (the same sandboxed fetcher used by ingest),
 *  2. backend returns deduped grounded candidates, operator picks which
 *     ones to commit. Apply is delegated to the caller via `onApply` —
 *     this component stays pure UI.
 */
export function SuggestRulesDialog({
  open,
  policyId,
  policyVersion,
  fetching,
  applying,
  suggestions,
  onFetchUrl,
  onFetchFile,
  onApply,
  onClose,
}: {
  open: boolean;
  policyId: string;
  policyVersion: string;
  fetching: boolean;
  applying: boolean;
  suggestions: SuggestedRule[] | null;
  onFetchUrl: (url: string) => Promise<void> | void;
  onFetchFile: (file: File) => Promise<void> | void;
  onApply: (selected: SuggestedRule[]) => Promise<void> | void;
  onClose: () => void;
}) {
  const t = useTranslations('policies.suggest');
  const [mode, setMode] = useState<SuggestMode>('url');
  const [url, setUrl] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [selectedIdx, setSelectedIdx] = useState<Set<number>>(new Set());
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!open) {
      setMode('url');
      setUrl('');
      setFile(null);
      setSelectedIdx(new Set());
    }
  }, [open]);

  // When fresh suggestions arrive, default to all selected (operator can
  // uncheck unwanted ones). Empty list -> empty selection.
  useEffect(() => {
    if (suggestions) {
      setSelectedIdx(new Set(suggestions.map((_, i) => i)));
    }
  }, [suggestions]);

  if (!open) return null;

  const toggle = (i: number) => {
    setSelectedIdx((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });
  };

  const hasResults = suggestions !== null;
  const busy = fetching || applying;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-bg-canvas/70 backdrop-blur-sm"
      onClick={busy ? undefined : onClose}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        className="flex max-h-[90vh] w-[min(720px,94vw)] flex-col rounded-xl border border-border surface-elev p-5 shadow-popover"
      >
        <div className="flex items-start gap-2">
          <Sparkles size={16} className="mt-0.5 text-status-info" />
          <div>
            <div className="text-[10px] uppercase tracking-[0.2em] text-text-muted">
              {t('eyebrow')}
            </div>
            <h3 className="text-sm font-semibold">
              {t('title', { id: policyId, version: policyVersion })}
            </h3>
            <p className="mt-1 text-xs text-text-muted">{t('desc')}</p>
          </div>
        </div>

        {!hasResults ? (
          <>
            <div
              className="mt-4 inline-flex rounded-md border border-border p-0.5"
              role="tablist"
              aria-label={t('modeAria')}
            >
              {(['url', 'file'] as SuggestMode[]).map((m) => (
                <button
                  key={m}
                  type="button"
                  role="tab"
                  aria-selected={mode === m}
                  onClick={() => setMode(m)}
                  disabled={fetching}
                  className={cn(
                    'flex items-center gap-1.5 rounded px-3 py-1 text-xs',
                    mode === m
                      ? 'bg-bg-panel-elev font-semibold text-text-primary'
                      : 'text-text-muted hover:text-text-primary'
                  )}
                >
                  {m === 'url' ? <LinkIcon size={12} /> : <FileText size={12} />}
                  {t(m === 'url' ? 'modeUrl' : 'modeFile')}
                </button>
              ))}
            </div>
            {mode === 'url' ? (
              <input
                autoFocus
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder={t('urlPlaceholder')}
                className="mt-3 h-9 w-full rounded-md border border-border bg-bg-canvas px-3 text-xs outline-none focus:border-status-info/60 focus:ring-2 focus:ring-status-info/20"
                disabled={fetching}
              />
            ) : (
              <div className="mt-3 flex items-center gap-3">
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.docx,.md,.txt,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/plain,text/markdown"
                  className="hidden"
                  onChange={(e) => {
                    const f = e.target.files?.[0] ?? null;
                    e.target.value = '';
                    setFile(f);
                  }}
                  disabled={fetching}
                />
                <Button
                  size="sm"
                  variant="secondary"
                  onClick={() => fileInputRef.current?.click()}
                  disabled={fetching}
                >
                  {t('chooseFile')}
                </Button>
                <span className="truncate text-xs text-text-muted">
                  {file ? file.name : t('noFile')}
                </span>
              </div>
            )}
            {fetching && (
              <div className="mt-3">
                <div className="text-[10px] uppercase tracking-wide text-text-muted">
                  {t('fetching')}
                </div>
                <Progress className="mt-1.5" value={0} indeterminate />
              </div>
            )}
          </>
        ) : (
          <div className="mt-4 flex-1 overflow-auto rounded-md border border-border bg-bg-canvas">
            {suggestions.length === 0 ? (
              <div className="p-6 text-center text-xs text-text-muted">{t('noSuggestions')}</div>
            ) : (
              <ul className="divide-y divide-border">
                {suggestions.map((s, i) => (
                  <li key={i} className="flex items-start gap-3 px-3 py-2">
                    <input
                      type="checkbox"
                      checked={selectedIdx.has(i)}
                      onChange={() => toggle(i)}
                      className="mt-1"
                      aria-label={t('toggleAria', { excerpt: s.excerpt })}
                    />
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2 text-[10px] uppercase tracking-wide text-text-muted">
                        <span>{s.rule_type}</span>
                        <span aria-hidden>·</span>
                        <span>{s.severity}</span>
                      </div>
                      <p className="mt-1 text-xs italic leading-5 text-text-primary break-words">
                        &ldquo;{s.excerpt}&rdquo;
                      </p>
                      {s.rationale ? (
                        <p className="mt-1 text-[11px] text-text-muted leading-5">{s.rationale}</p>
                      ) : null}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        <div className="mt-5 flex items-center justify-between gap-2">
          <span className="text-[11px] text-text-muted">
            {hasResults
              ? t('countSelected', {
                  selected: selectedIdx.size,
                  total: suggestions?.length ?? 0,
                })
              : t('hintGrounding')}
          </span>
          <div className="flex gap-2">
            <Button size="sm" variant="ghost" onClick={onClose} disabled={busy}>
              {t('cancel')}
            </Button>
            {!hasResults ? (
              <Button
                size="sm"
                variant="primary"
                onClick={() => {
                  if (mode === 'url') void onFetchUrl(url);
                  else if (file) void onFetchFile(file);
                }}
                disabled={fetching || (mode === 'url' ? !url.trim() : !file)}
              >
                {fetching ? t('fetching') : t('fetch')}
              </Button>
            ) : (
              <Button
                size="sm"
                variant="primary"
                onClick={() => {
                  const picked = (suggestions ?? []).filter((_, i) => selectedIdx.has(i));
                  void onApply(picked);
                }}
                disabled={applying || selectedIdx.size === 0}
              >
                {applying ? t('applying') : t('applyN', { n: selectedIdx.size })}
              </Button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
