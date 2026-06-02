import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { Virtuoso, type VirtuosoHandle } from 'react-virtuoso';
import type { AttackSurfaceResp, CyEdge, CyNode } from '../../../lib/api';
import { Icon } from '../Icon';
import { Bubble } from './parts/Bubble';
import { EmptyChat } from './parts/EmptyChat';
import { loadMessages, persistMessages } from './storage';
import { streamChat, uid } from './stream';
import { buildSuggestions, compactLabel } from './suggestions';
import type { ChatMessage, FocusInfo, Role } from './types';

export function GraphChat({
  data,
  target,
  scanId,
  focus,
  onCitationClick,
  onClearFocus,
}: {
  data: AttackSurfaceResp | null;
  target: string;
  scanId?: string | null;
  focus?: FocusInfo | null;
  onCitationClick?: (id: string) => void;
  onClearFocus?: () => void;
}) {
  const [messages, setMessages] = useState<ChatMessage[]>(() => loadMessages(target));
  const [input, setInput] = useState('');
  const [streaming, setStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const virtuosoRef = useRef<VirtuosoHandle | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const lastPayloadRef = useRef<object | null>(null);

  const citationLabels = useMemo(() => {
    const m = new Map<string, string>();
    for (const n of data?.nodes ?? []) {
      const display = n.data.display && n.data.display !== n.data.id ? n.data.display : '';
      if (display) m.set(n.data.id, display);
    }
    return m;
  }, [data]);

  useEffect(() => {
    setMessages(loadMessages(target));
  }, [target]);

  useEffect(() => {
    persistMessages(target, messages);
  }, [target, messages]);

  // Auto-resize textarea up to a cap.
  useLayoutEffect(() => {
    const el = inputRef.current;
    if (!el) return;
    el.style.height = 'auto';
    const next = Math.min(el.scrollHeight, 180);
    el.style.height = `${next}px`;
  }, [input]);

  const focusIds = useMemo(() => (focus ? [focus.id] : []), [focus]);
  const suggestions = useMemo(() => buildSuggestions(data, focus), [data, focus]);

  const buildBody = useCallback(
    (q: string, history: { role: Role; content: string }[]) => {
      if (!data) return null;
      return {
        question: q,
        nodes: data.nodes.map((n: CyNode) => ({ data: n.data })),
        edges: data.edges.map((e: CyEdge) => ({ data: e.data })),
        focus_ids: focusIds,
        scan_id: scanId ?? null,
        target,
        history,
      };
    },
    [data, focusIds, scanId, target]
  );

  const runStream = useCallback(async (placeholderId: string, body: object) => {
    lastPayloadRef.current = body;
    setStreaming(true);
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    const startedAt = Date.now();

    try {
      for await (const evt of streamChat(body, ctrl.signal)) {
        if (evt.type === 'start') {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === placeholderId ? { ...m, promptChars: evt.promptChars, startedAt } : m
            )
          );
        } else if (evt.type === 'delta') {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === placeholderId ? { ...m, content: m.content + evt.text, pending: true } : m
            )
          );
        } else if (evt.type === 'error') {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === placeholderId
                ? { ...m, pending: false, error: evt.message, endedAt: Date.now() }
                : m
            )
          );
        } else if (evt.type === 'end') {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === placeholderId ? { ...m, pending: false, endedAt: Date.now() } : m
            )
          );
        }
      }
    } catch (err) {
      const aborted = (err as Error).name === 'AbortError';
      setMessages((prev) =>
        prev.map((m) =>
          m.id === placeholderId
            ? {
                ...m,
                pending: false,
                error: aborted ? 'aborted' : String(err),
                endedAt: Date.now(),
              }
            : m
        )
      );
    } finally {
      setStreaming(false);
      abortRef.current = null;
    }
  }, []);

  const send = useCallback(async () => {
    const q = input.trim();
    if (!q || streaming || !data) return;
    setInput('');
    const userMsg: ChatMessage = { id: uid(), role: 'user', content: q };
    const placeholder: ChatMessage = { id: uid(), role: 'assistant', content: '', pending: true };
    const history = messages
      .filter((m) => !m.pending && !m.error)
      .slice(-12)
      .map((m) => ({ role: m.role, content: m.content }));
    const body = buildBody(q, history);
    if (!body) return;
    setMessages((prev) => [...prev, userMsg, placeholder]);
    await runStream(placeholder.id, body);
  }, [buildBody, data, input, messages, runStream, streaming]);

  const regenerate = useCallback(
    async (assistantId: string) => {
      if (streaming || !data) return;
      const idx = messages.findIndex((m) => m.id === assistantId);
      if (idx <= 0) return;
      const userMsg = messages[idx - 1];
      if (!userMsg || userMsg.role !== 'user') return;
      const history = messages
        .slice(0, idx - 1)
        .filter((m) => !m.pending && !m.error)
        .slice(-12)
        .map((m) => ({ role: m.role, content: m.content }));
      const body = buildBody(userMsg.content, history);
      if (!body) return;
      setMessages((prev) => {
        const next = prev.slice();
        next[idx] = { ...next[idx]!, content: '', pending: true, error: null, endedAt: undefined };
        return next;
      });
      await runStream(assistantId, body);
    },
    [buildBody, data, messages, runStream, streaming]
  );

  const stop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const clear = useCallback(() => {
    setMessages([]);
    persistMessages(target, []);
  }, [target]);

  const onKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.altKey) {
      e.preventDefault();
      void send();
    } else if (e.key === 'Escape' && streaming) {
      e.preventDefault();
      stop();
    }
  };

  // Global Cmd/Ctrl+K to focus input.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  const stats = useMemo(() => {
    if (!data) return null;
    return `${data.nodes.length} nodes · ${data.edges.length} edges`;
  }, [data]);

  return (
    <div className="flex h-full min-h-0 flex-col rounded-lg border border-bg-line bg-bg-base/70 shadow-elevated backdrop-blur">
      <header className="flex min-h-[52px] items-center justify-between gap-2 border-b border-bg-line px-3 py-2 pr-11 xl:pr-3">
        <div className="min-w-0">
          <p className="flex items-center gap-1.5 text-2xs font-mono uppercase tracking-wider text-text-muted">
            <Icon.Graph size={13} className="text-brand" />
            Graph chat
          </p>
          <p className="truncate text-2xs text-text-muted">{stats ?? 'load a graph to start'}</p>
        </div>
        <div className="flex items-center gap-1">
          <button
            type="button"
            onClick={clear}
            className="grid h-8 w-8 place-items-center rounded-md text-text-muted transition hover:bg-bg-overlay hover:text-text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-brand/40 disabled:cursor-not-allowed disabled:opacity-40"
            disabled={messages.length === 0 || streaming}
            title="Clear conversation"
            aria-label="Clear conversation"
          >
            <Icon.Trash size={14} />
          </button>
        </div>
      </header>

      {focus && (
        <div className="flex min-h-[36px] items-center gap-2 border-b border-bg-line bg-bg-overlay/60 px-3 py-1.5">
          <span className="text-2xs font-mono uppercase tracking-wider text-text-muted">Focus</span>
          <span className="truncate font-mono text-2xs text-brand" title={focus.id}>
            {focus.display}
          </span>
          <span className="ml-auto rounded bg-bg-base px-1 font-mono text-[10px] uppercase text-text-muted">
            {focus.label}
          </span>
          <button
            type="button"
            onClick={() => {
              setInput(`Assess the risk around ${compactLabel(focus.display)}.`);
              inputRef.current?.focus();
            }}
            className="grid h-6 w-6 place-items-center rounded text-text-muted transition hover:bg-bg-base hover:text-brand focus:outline-none focus-visible:ring-2 focus-visible:ring-brand/40"
            aria-label="Ask about focused node"
            title="Ask about focused node"
          >
            <Icon.Sparkles size={12} />
          </button>
          {onClearFocus && (
            <button
              type="button"
              onClick={onClearFocus}
              className="grid h-6 w-6 place-items-center rounded text-text-muted transition hover:bg-bg-base hover:text-text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-brand/40"
              aria-label="Clear focused node"
              title="Clear focused node"
            >
              <Icon.X size={12} />
            </button>
          )}
        </div>
      )}

      <div
        className="min-h-0 flex-1"
        role="log"
        aria-live="polite"
        aria-relevant="additions"
        aria-busy={streaming}
      >
        {messages.length === 0 ? (
          <EmptyChat
            disabled={!data}
            suggestions={suggestions}
            onPick={(s) => {
              setInput(s);
              inputRef.current?.focus();
            }}
          />
        ) : (
          <Virtuoso
            ref={virtuosoRef}
            data={messages}
            followOutput="auto"
            atBottomThreshold={120}
            initialTopMostItemIndex={messages.length - 1}
            className="h-full"
            itemContent={(_, m) => (
              <div className="px-3 py-1.5 first:pt-3 last:pb-3">
                <Bubble
                  msg={m}
                  onCitationClick={onCitationClick}
                  citationLabels={citationLabels}
                  onRegenerate={() => regenerate(m.id)}
                  canRegenerate={!streaming && m.role === 'assistant'}
                />
              </div>
            )}
          />
        )}
      </div>

      <div className="border-t border-bg-line bg-bg-base/65 p-2">
        <div className="relative">
          <textarea
            ref={inputRef}
            rows={1}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder={
              data
                ? 'Chiedi correlazioni, attack path, blast radius...'
                : 'Carica un grafo prima di chattare…'
            }
            disabled={!data}
            aria-label="Graph chat prompt"
            className="ra-input w-full resize-none pr-12 font-body text-sm leading-snug"
            style={{ minHeight: 40 }}
          />
          <div className="absolute bottom-2 right-2 flex items-center gap-1.5">
            {streaming ? (
              <button
                type="button"
                onClick={stop}
                className="grid h-7 w-7 place-items-center rounded-md bg-sev-critical/20 text-sev-critical transition hover:bg-sev-critical/30 focus:outline-none focus-visible:ring-2 focus-visible:ring-sev-critical/40"
                aria-label="Stop generation"
                title="Stop generation"
              >
                <Icon.X size={13} />
              </button>
            ) : (
              <button
                type="button"
                onClick={() => void send()}
                disabled={!input.trim() || !data}
                className="grid h-7 w-7 place-items-center rounded-md bg-brand/20 text-brand transition hover:bg-brand/30 focus:outline-none focus-visible:ring-2 focus-visible:ring-brand/40 disabled:cursor-not-allowed disabled:opacity-40"
                aria-label="Send message"
                title="Send message"
              >
                <Icon.ArrowUp size={14} />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
