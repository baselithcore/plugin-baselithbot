import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { Virtuoso, type VirtuosoHandle } from 'react-virtuoso';
import type { AttackSurfaceResp, CyEdge, CyNode } from '../../lib/api';
import { getToken } from '../../lib/api';
import { Icon } from './Icon';
import { Markdown } from './Markdown';

type Role = 'user' | 'assistant';

interface ChatMessage {
  id: string;
  role: Role;
  content: string;
  pending?: boolean;
  error?: string | null;
  startedAt?: number;
  endedAt?: number;
  promptChars?: number;
}

interface FocusInfo {
  id: string;
  label: string;
  display: string;
}

type SuggestionGroup = { group: string; items: string[] };

const STORAGE_KEY = (target: string) => `red_agent.graph_chat.${target}`;
const MAX_PERSIST_TURNS = 30;
const FALLBACK_SUGGESTIONS: SuggestionGroup[] = [
  {
    group: 'Risk',
    items: ['Top 3 findings to prioritize. Why?', 'Worst blast radius in this graph.'],
  },
  {
    group: 'Attack paths',
    items: ['Show likely attack paths.', 'Plausible lateral movement between identities.'],
  },
  {
    group: 'Coverage',
    items: ['Assets under-covered by scanners.'],
  },
];

function uid(): string {
  return Math.random().toString(36).slice(2, 10);
}

async function* streamChat(
  body: object,
  signal: AbortSignal
): AsyncGenerator<
  | { type: 'start'; promptChars: number }
  | { type: 'delta'; text: string }
  | { type: 'error'; message: string }
  | { type: 'end' }
> {
  const res = await fetch('/red-agent/graph/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      Authorization: `Bearer ${getToken()}`,
    },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok) {
    yield { type: 'error', message: `${res.status} ${await res.text()}` };
    return;
  }
  if (!res.body) {
    yield { type: 'error', message: 'No response body' };
    return;
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let sepIdx: number;
    while ((sepIdx = buffer.indexOf('\n\n')) !== -1) {
      const block = buffer.slice(0, sepIdx);
      buffer = buffer.slice(sepIdx + 2);
      const evt = parseSseBlock(block);
      if (!evt) continue;
      if (evt.event === 'start') {
        yield { type: 'start', promptChars: Number(evt.data?.prompt_chars ?? 0) };
      } else if (evt.event === 'delta' && typeof evt.data?.text === 'string') {
        yield { type: 'delta', text: evt.data.text };
      } else if (evt.event === 'end') {
        yield { type: 'end' };
      } else if (evt.event === 'error') {
        yield { type: 'error', message: String(evt.data?.message ?? 'unknown error') };
      }
    }
  }
}

function parseSseBlock(block: string): { event: string; data: Record<string, unknown> } | null {
  let event = 'message';
  const dataLines: string[] = [];
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim();
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
  }
  if (dataLines.length === 0) return null;
  const raw = dataLines.join('\n');
  try {
    return { event, data: JSON.parse(raw) as Record<string, unknown> };
  } catch {
    return { event, data: { text: raw } };
  }
}

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

function EmptyChat({
  disabled,
  suggestions,
  onPick,
}: {
  disabled: boolean;
  suggestions: SuggestionGroup[];
  onPick: (s: string) => void;
}) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 px-4 py-6">
      <div className="grid h-10 w-10 place-items-center rounded-lg border border-bg-line bg-bg-overlay text-brand">
        <Icon.Sparkles size={16} />
      </div>
      <p className="text-center text-xs text-text-muted">
        {disabled ? 'Carica un grafo per chattare.' : 'Comincia con una domanda:'}
      </p>
      {!disabled && (
        <div className="flex w-full max-w-md flex-col gap-2.5">
          {suggestions.map((g) => (
            <div key={g.group}>
              <p className="mb-1 text-2xs font-mono uppercase tracking-wider text-text-muted">
                {g.group}
              </p>
              <ul className="flex flex-col gap-1">
                {g.items.map((s) => (
                  <li key={s}>
                    <button
                      type="button"
                      onClick={() => onPick(s)}
                      className="w-full rounded-md border border-bg-line bg-bg-overlay px-3 py-2 text-left font-body text-xs text-text-secondary transition-colors hover:border-brand/40 hover:bg-bg-hover/70 hover:text-text-primary focus:outline-none focus-visible:ring-2 focus-visible:ring-brand/40"
                    >
                      {s}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Bubble({
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

function loadMessages(target: string): ChatMessage[] {
  if (!target) return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY(target));
    if (!raw) return [];
    const parsed = JSON.parse(raw) as ChatMessage[];
    return parsed.filter((m) => !m.pending);
  } catch {
    return [];
  }
}

function persistMessages(target: string, messages: ChatMessage[]): void {
  if (!target) return;
  try {
    const trimmed = messages
      .filter((m) => !m.pending)
      .slice(-MAX_PERSIST_TURNS)
      .map((m) => ({ ...m, error: m.error ?? null }));
    localStorage.setItem(STORAGE_KEY(target), JSON.stringify(trimmed));
  } catch {
    /* noop */
  }
}

function buildSuggestions(
  data: AttackSurfaceResp | null,
  focus?: FocusInfo | null
): SuggestionGroup[] {
  if (!data) return FALLBACK_SUGGESTIONS;

  let criticalHigh = 0;
  let vulnerabilities = 0;
  let identities = 0;
  let scanners = 0;
  let entryPoints = 0;
  for (const n of data.nodes) {
    if (n.data.label === 'Vulnerability') vulnerabilities++;
    if (n.data.severity === 'critical' || n.data.severity === 'high') criticalHigh++;
    if (n.data.label === 'Identity') identities++;
    if (n.data.label === 'Scanner') scanners++;
    if (['Target', 'Endpoint', 'Service', 'CloudResource', 'ApiSpec'].includes(n.data.label)) {
      entryPoints++;
    }
  }
  const lateralEdges = data.edges.filter((e) => e.data.type === 'LATERAL_TO').length;
  const groups: SuggestionGroup[] = [];

  if (focus) {
    const label = compactLabel(focus.display);
    groups.push({
      group: 'Focus',
      items: [`Assess the risk around ${label}.`, `Find attack paths involving ${label}.`],
    });
  }

  groups.push({
    group: 'Risk',
    items:
      criticalHigh > 0
        ? [
            `Prioritize the top ${Math.min(3, criticalHigh)} critical/high findings.`,
            `What is the worst blast radius across ${entryPoints} entry points?`,
          ]
        : [
            `Summarize the risk posture across ${vulnerabilities} findings.`,
            'Which low-signal findings can wait?',
          ],
  });

  if (identities > 0 || lateralEdges > 0) {
    groups.push({
      group: 'Attack paths',
      items: [
        lateralEdges > 0
          ? `Explain the ${lateralEdges} lateral movement relation${lateralEdges === 1 ? '' : 's'}.`
          : `Check whether ${identities} identity node${identities === 1 ? '' : 's'} create attack paths.`,
        'Which path should an analyst validate first?',
      ],
    });
  }

  groups.push({
    group: 'Coverage',
    items: [
      scanners > 0
        ? `Which assets lack evidence from the ${scanners} scanner node${scanners === 1 ? '' : 's'}?`
        : 'Which assets look under-covered by scanners?',
    ],
  });

  return groups.slice(0, 3);
}

function compactLabel(value: string): string {
  const trimmed = value.trim();
  if (trimmed.length <= 52) return trimmed;
  return `${trimmed.slice(0, 49)}...`;
}
