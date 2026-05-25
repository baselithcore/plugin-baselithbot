'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { ShieldAlert, Sparkles, X } from 'lucide-react';
import { useTranslations } from 'next-intl';
import { askFindingStream, type Finding } from '@/lib/api';
import { useAppStore } from '@/lib/store';
import { SeverityBadge } from '@/components/ui/badge';
import { Banner, ThinkingIndicator, type T } from './ask/atoms';
import { ChatTurn, type QA } from './ask/ChatTurn';
import { Composer } from './ask/Composer';
import { ContextInspector } from './ask/ContextInspector';
import { EmptyState } from './ask/EmptyState';

const MAX_CHARS = 2000;

export function AskModal() {
  const t = useTranslations('ask');
  const finding = useAppStore((s) => s.askFor);
  const setAskFor = useAppStore((s) => s.setAskFor);
  const report = useAppStore((s) => s.currentReport);

  const [question, setQuestion] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<QA[]>([]);
  const [contextOpen, setContextOpen] = useState(false);

  const inputRef = useRef<HTMLTextAreaElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (finding) {
      setQuestion('');
      setError(null);
      setHistory([]);
      setContextOpen(false);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [finding?.id]);

  useEffect(() => {
    if (!finding) return;
    function onKey(e: KeyboardEvent) {
      if (e.key === 'Escape') setAskFor(null);
    }
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [finding, setAskFor]);

  // Auto-resize textarea up to a sensible cap.
  useEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 180)}px`;
  }, [question]);

  // Auto-scroll on new turn or while busy (typing indicator).
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: 'smooth',
    });
  }, [history.length, busy]);

  const reportId = report?.report_id;
  const charCount = question.length;
  const overLimit = charCount > MAX_CHARS;
  const canSubmit = !!reportId && !busy && question.trim().length > 1 && !overLimit;

  const suggestions = useMemo(
    () => (finding ? [t('suggestion1'), t('suggestion2'), t('suggestion3'), t('suggestion4')] : []),
    [finding, t]
  );

  if (!finding) return null;

  async function runAsk(qText: string) {
    if (!finding || !reportId) return;
    const q = qText.trim();
    if (!q) return;
    setBusy(true);
    setError(null);
    setQuestion('');

    // Optimistic user turn + empty assistant placeholder marked streaming.
    const ts = Date.now();
    setHistory((h) => [...h, { q, a: '', grounded: false, ts, streaming: true }]);

    const updateLast = (mut: (qa: QA) => QA) =>
      setHistory((h) => {
        if (h.length === 0) return h;
        const copy = h.slice();
        copy[copy.length - 1] = mut(copy[copy.length - 1]);
        return copy;
      });

    try {
      await askFindingStream(reportId, finding.id, q, {
        onToken: (text) => updateLast((qa) => ({ ...qa, a: qa.a + text })),
        onDone: (full, grounded) =>
          updateLast((qa) => ({
            ...qa,
            a: full || qa.a,
            grounded,
            streaming: false,
          })),
        onError: (msg) => {
          updateLast((qa) => ({ ...qa, streaming: false }));
          setError(msg);
        },
      });
    } catch (err) {
      updateLast((qa) => ({ ...qa, streaming: false }));
      setError(err instanceof Error ? err.message : t('errorFailed'));
    } finally {
      setBusy(false);
    }
  }

  async function submit() {
    if (!canSubmit) return;
    await runAsk(question);
  }

  async function retry(idx: number) {
    const item = history[idx];
    if (!item) return;
    setHistory((h) => h.slice(0, idx));
    await runAsk(item.q);
  }

  return (
    <>
      <div
        onClick={() => setAskFor(null)}
        className="fixed inset-0 bg-bg-canvas/50 backdrop-blur-[3px] z-30 animate-fade-in"
      />
      <aside
        role="dialog"
        aria-label={t('title')}
        className="fixed top-0 right-0 bottom-0 w-[min(680px,100vw)] surface-elev border-l border-border z-40 flex flex-col animate-slide-up shadow-popover"
      >
        <Header finding={finding} onClose={() => setAskFor(null)} t={t} />

        <ContextInspector
          finding={finding}
          open={contextOpen}
          onToggle={() => setContextOpen((v) => !v)}
          t={t}
        />

        <div ref={scrollRef} className="flex-1 overflow-auto px-5 py-5 space-y-5 scroll-smooth">
          {!reportId && (
            <Banner tone="warning" icon={ShieldAlert}>
              {t('noReport')}
            </Banner>
          )}

          {history.length === 0 && reportId && (
            <EmptyState t={t} suggestions={suggestions} onPick={(s) => runAsk(s)} disabled={busy} />
          )}

          {history.map((qa, i) => (
            <ChatTurn
              key={`${qa.ts}-${i}`}
              qa={qa}
              t={t}
              onRetry={() => retry(i)}
              disabled={busy}
            />
          ))}

          {busy && !history[history.length - 1]?.streaming && <ThinkingIndicator t={t} />}

          {error && (
            <Banner tone="danger" icon={ShieldAlert}>
              {error}
            </Banner>
          )}
        </div>

        <Composer
          ref={inputRef}
          value={question}
          onChange={setQuestion}
          onSubmit={submit}
          busy={busy}
          canSubmit={canSubmit}
          charCount={charCount}
          overLimit={overLimit}
          maxChars={MAX_CHARS}
          disabled={!reportId}
          historyCount={history.length}
          onClearChat={() => setHistory([])}
          t={t}
        />
      </aside>
    </>
  );
}

function Header({ finding, onClose, t }: { finding: Finding; onClose: () => void; t: T }) {
  return (
    <header className="px-5 py-4 border-b border-border bg-gradient-to-b from-bg-panel-elev/40 to-transparent">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-text-muted inline-flex items-center gap-1.5">
            <Sparkles size={12} className="text-status-info" />
            {t('title')}
          </div>
          <div className="mt-1.5 flex items-center gap-2">
            <SeverityBadge severity={finding.severity} />
            <span className="truncate text-[12px] font-mono text-text-secondary">
              {finding.rule_id}
            </span>
            <span className="hidden sm:inline text-[10px] font-mono text-text-muted">
              · {finding.policy_ref.policy_id}@{finding.policy_ref.version}
            </span>
          </div>
          <p className="mt-2 text-[12.5px] leading-5 text-text-secondary line-clamp-2">
            {finding.explanation}
          </p>
        </div>
        <button
          type="button"
          onClick={onClose}
          aria-label={t('close')}
          className="p-1.5 rounded-md hover:bg-bg-panel-elev text-text-muted hover:text-text-primary transition-colors ring-focus"
        >
          <X size={16} />
        </button>
      </div>
    </header>
  );
}
