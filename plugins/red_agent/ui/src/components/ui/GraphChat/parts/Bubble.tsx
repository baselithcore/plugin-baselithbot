import { useState } from 'react';
import { Icon } from '../../Icon';
import { Markdown } from '../../Markdown';
import type { ChatMessage } from '../types';

export function Bubble({
  msg,
  onCitationClick,
  citationLabels,
  onRegenerate,
  canRegenerate,
}: {
  msg: ChatMessage;
  onCitationClick?: (id: string) => void;
  citationLabels?: Map<string, string>;
  onRegenerate: () => void;
  canRegenerate: boolean;
}) {
  const isUser = msg.role === 'user';
  const tone = isUser ? 'border-brand/30 bg-brand/10' : 'border-bg-line bg-bg-card/90';
  const [copied, setCopied] = useState(false);
  const copy = () => {
    void navigator.clipboard.writeText(msg.content).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1400);
    });
  };
  const latencyMs = msg.startedAt && msg.endedAt ? msg.endedAt - msg.startedAt : null;

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`group max-w-[92%] rounded-lg border px-3 py-2 shadow-card ${
          isUser ? 'rounded-tr-sm' : 'rounded-tl-sm'
        } ${tone}`}
      >
        <div className="mb-1 flex items-center gap-2 text-2xs font-mono uppercase tracking-wider text-text-muted">
          <span className="inline-flex items-center gap-1.5">
            {isUser ? <Icon.User size={11} /> : <Icon.Sparkles size={11} />}
            {isUser ? 'you' : 'analyst'}
          </span>
          {msg.pending && <span className="animate-pulse text-brand">streaming</span>}
          {msg.error && <span className="text-sev-critical">err</span>}
          {!msg.pending && latencyMs != null && (
            <span title="response latency">{(latencyMs / 1000).toFixed(1)}s</span>
          )}
          {msg.promptChars != null && msg.promptChars > 0 && (
            <span title="prompt chars">{msg.promptChars}c</span>
          )}
        </div>

        {isUser ? (
          <div className="whitespace-pre-wrap break-words text-sm leading-relaxed text-text-primary">
            {msg.content}
          </div>
        ) : (
          <>
            {msg.content ? (
              <Markdown
                source={msg.content}
                onCitationClick={onCitationClick}
                citationLabels={citationLabels}
              />
            ) : (
              msg.pending && <span className="text-text-muted">thinking…</span>
            )}
            {msg.pending && msg.content && (
              <span className="ml-0.5 inline-block h-3 w-1 animate-pulse bg-brand align-middle" />
            )}
          </>
        )}

        {msg.error && <div className="mt-1 font-mono text-2xs text-sev-critical">{msg.error}</div>}

        {!isUser && !msg.pending && (msg.content || msg.error) && (
          <div className="mt-2 flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100 focus-within:opacity-100">
            <button
              type="button"
              onClick={copy}
              className="inline-flex h-7 items-center gap-1 rounded-md px-1.5 font-mono text-[10px] uppercase tracking-wider text-text-muted transition hover:bg-bg-overlay hover:text-text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-brand/40"
              aria-label="Copy answer"
              title="Copy answer"
            >
              <Icon.Copy size={12} />
              {copied && <span>copied</span>}
            </button>
            {canRegenerate && (
              <button
                type="button"
                onClick={onRegenerate}
                className="grid h-7 w-7 place-items-center rounded-md text-text-muted transition hover:bg-bg-overlay hover:text-text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-brand/40"
                aria-label="Regenerate answer"
                title="Regenerate answer"
              >
                <Icon.Refresh size={12} />
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
