/**
 * useEmbedChat — fork minimale di ``useChat`` per la mini-app embed.
 *
 * Differenze rispetto al main ``useChat``:
 *
 * - Niente conversation_id server (stateless). History interamente
 *   client-side, persistita opzionalmente in ``localStorage`` con chiave
 *   ``wiki_embed_history_<token_first8>``.
 * - Niente trace agentic / memorie / citation warnings — UI semplificata.
 * - Niente regenerate / editAndResend (l'embed è disposable).
 * - Niente auto-refresh JWT (no auth).
 */

import { useCallback, useRef, useState } from 'react';

import { streamEmbedChat, type EmbedSource, type EmbedStreamEvent } from './api';

export interface EmbedMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: EmbedSource[];
  streaming?: boolean;
  error?: string;
}

export interface UseEmbedChatOptions {
  token: string;
  historyKey?: string;
  maxHistoryTurns?: number;
}

let _idSeq = 0;
const _uid = () => `m${Date.now().toString(36)}-${(_idSeq++).toString(36)}`;

function loadHistory(key: string): EmbedMessage[] {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as EmbedMessage[];
    if (!Array.isArray(parsed)) return [];
    return parsed.filter((m) => m && (m.role === 'user' || m.role === 'assistant'));
  } catch {
    return [];
  }
}

function saveHistory(key: string, messages: EmbedMessage[]): void {
  try {
    // Salva solo messaggi completi (no streaming flag) per non corrompere
    // il restore se il tab viene chiuso a metà stream.
    const complete = messages.filter((m) => !m.streaming);
    localStorage.setItem(key, JSON.stringify(complete.slice(-40)));
  } catch {
    /* quota / private mode — silent fail */
  }
}

export function useEmbedChat(opts: UseEmbedChatOptions) {
  const historyKey = opts.historyKey ?? `wiki_embed_history_${opts.token.slice(0, 12)}`;
  const [messages, setMessages] = useState<EmbedMessage[]>(() => loadHistory(historyKey));
  const [isStreaming, setIsStreaming] = useState(false);
  const [lastError, setLastError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const persist = useCallback(
    (next: EmbedMessage[]) => {
      saveHistory(historyKey, next);
    },
    [historyKey]
  );

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setMessages([]);
    setLastError(null);
    try {
      localStorage.removeItem(historyKey);
    } catch {
      /* noop */
    }
  }, [historyKey]);

  const stop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const send = useCallback(
    async (content: string) => {
      const trimmed = content.trim();
      if (!trimmed || isStreaming) return;

      const userMsg: EmbedMessage = { id: _uid(), role: 'user', content: trimmed };
      const asstId = _uid();
      const asstMsg: EmbedMessage = { id: asstId, role: 'assistant', content: '', streaming: true };

      const historyForBackend = messages
        .filter((m) => !m.streaming && !m.error)
        .slice(-(opts.maxHistoryTurns ?? 20))
        .map((m) => ({ role: m.role, content: m.content }));

      setMessages((prev) => [...prev, userMsg, asstMsg]);
      setIsStreaming(true);
      setLastError(null);

      const ctrl = new AbortController();
      abortRef.current = ctrl;

      const onEvent = (ev: EmbedStreamEvent) => {
        if (ev.type === 'done') {
          setIsStreaming(false);
          setMessages((prev) => {
            const next = prev.map((m) => (m.id === asstId ? { ...m, streaming: false } : m));
            persist(next);
            return next;
          });
          return;
        }
        if (ev.type === 'token') {
          const token = (ev as { content: string }).content ?? '';
          setMessages((prev) =>
            prev.map((m) => (m.id === asstId ? { ...m, content: m.content + token } : m))
          );
          return;
        }
        if (ev.type === 'sources') {
          const items = (ev as { items: EmbedSource[] }).items ?? [];
          setMessages((prev) =>
            prev.map((m) => (m.id === asstId ? { ...m, sources: items } : m))
          );
          return;
        }
        if (ev.type === 'error') {
          const msg = (ev as { message: string }).message ?? 'errore stream';
          setLastError(msg);
          setMessages((prev) =>
            prev.map((m) => (m.id === asstId ? { ...m, error: msg, streaming: false } : m))
          );
          return;
        }
      };

      try {
        await streamEmbedChat(opts.token, trimmed, historyForBackend, onEvent, {
          signal: ctrl.signal,
        });
      } catch (err) {
        const e = err as Error;
        if (e.name !== 'AbortError') {
          const msg = e.message ?? 'errore di rete';
          setLastError(msg);
          setMessages((prev) => {
            const next = prev.map((m) =>
              m.id === asstId ? { ...m, error: msg, streaming: false } : m
            );
            persist(next);
            return next;
          });
        } else {
          setMessages((prev) =>
            prev.map((m) => (m.id === asstId ? { ...m, streaming: false } : m))
          );
        }
      } finally {
        if (abortRef.current === ctrl) {
          setIsStreaming(false);
          abortRef.current = null;
        }
      }
    },
    [isStreaming, messages, opts.token, opts.maxHistoryTurns, persist]
  );

  return { messages, isStreaming, lastError, send, stop, reset };
}
