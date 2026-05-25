import { useCallback, useRef, useState } from 'react';
import type { Message, Source, StreamEvent } from '../lib/types';
import { streamChat } from '../lib/api';
import { truncateMessagesFrom } from '../lib/api/conversations';
import { uid } from '../lib/cn';

export interface UseChatOptions {
  graph?: boolean;
  limit?: number;
  /**
   * Id conversation persistita lato backend. Quando passato (utente
   * loggato), il router /api/chat/stream carica history + memorie e
   * persiste user/assistant turns. Quando assente, il backend
   * auto-crea conversation e comunica id via evento `conversation` —
   * `onConversationId` callback notifica al chiamante per sync state.
   *
   * Forma `Ref<string | null>` per evitare ciclo di dependency con
   * `useConversations` in App.tsx (vedi commento ref-based wiring).
   * Forma `string | null` accettata per back-compat / casi semplici.
   */
  conversationId?: string | null;
  conversationIdRef?: { readonly current: string | null };
  onConversationId?: (id: string) => void;
  /** Callback con id del messaggio assistant persistito (per feedback FK). */
  onAssistantMessageId?: (id: string) => void;
}

export interface UseChatResult {
  messages: Message[];
  isStreaming: boolean;
  lastError: string | null;
  send: (content: string) => Promise<void>;
  regenerate: () => Promise<void>;
  editAndResend: (messageId: string, content: string) => Promise<void>;
  stop: () => void;
  reset: () => void;
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
}

/**
 * Hook che gestisce la conversazione + streaming.
 *
 * Semantica eventi (dal backend `RAGAgent.stream`):
 *   agent → step → hits → agent → step → token* → sources → done
 *
 * L'assistente è un singolo Message che accumula token e riceve sources al
 * termine. `trace` contiene agent/step per disegnare il loader con sotto-stati.
 */
export function useChat(opts: UseChatOptions = {}): UseChatResult {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [lastError, setLastError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const send = useCallback(
    async (content: string) => {
      const trimmed = content.trim();
      if (!trimmed || isStreaming) return;

      const userMsg: Message = {
        id: uid(),
        role: 'user',
        content: trimmed,
        createdAt: Date.now(),
      };
      const asstId = uid();
      const startedAt = Date.now() + 1;
      const asstMsg: Message = {
        id: asstId,
        role: 'assistant',
        content: '',
        streaming: true,
        trace: [],
        createdAt: startedAt,
        startedAt,
      };

      // Snapshot history ANTE-send (solo turni completi) da mandare al backend
      const historyForBackend = messages.filter((m) => !m.streaming);

      setMessages((prev) => [...prev, userMsg, asstMsg]);
      setIsStreaming(true);
      setLastError(null);

      const ctrl = new AbortController();
      abortRef.current = ctrl;

      const onEvent = (ev: StreamEvent) => {
        const now = Date.now();
        // Eventi non-message-related: notifica callback senza toccare state.
        if (ev.type === 'conversation') {
          opts.onConversationId?.(ev.id);
          return;
        }
        if (ev.type === 'message_id') {
          opts.onAssistantMessageId?.(ev.id);
          return;
        }
        // `done` è il signal terminale UX: tokens + sources già emessi,
        // pulsante "Ferma" deve relax subito. Backend continua a yieldare
        // warnings post-stream (citation/groundedness/code/numeric guard)
        // che il `for await` di streamChat seguita a consumare — ma il
        // global `isStreaming` flippa qui, non quando lo stream chiude.
        if (ev.type === 'done') {
          setIsStreaming(false);
          setMessages((prev) =>
            prev.map((m) =>
              m.id === asstId ? { ...m, streaming: false, completedAt: now } : m
            )
          );
          return;
        }
        setMessages((prev) =>
          prev.map((m) => {
            if (m.id !== asstId) return m;
            switch (ev.type) {
              case 'agent':
                return {
                  ...m,
                  trace: [...(m.trace ?? []), { agent: ev.content, at: now }],
                };
              case 'step':
                return {
                  ...m,
                  trace: [...(m.trace ?? []), { step: ev.content, at: now }],
                };
              case 'hits':
                return m;
              case 'memories':
                // Aggiunge step diagnostic; lista memorie per ora non
                // renderizzata in UI (futura panel "memorie pertinenti").
                return {
                  ...m,
                  trace: [
                    ...(m.trace ?? []),
                    { step: `${ev.items.length} memoria/e personale recuperata`, at: now },
                  ],
                };
              case 'token':
                return {
                  ...m,
                  content: m.content + ev.content,
                  firstTokenAt: m.firstTokenAt ?? now,
                };
              case 'sources':
                return { ...m, sources: ev.items as Source[] };
              case 'query_rewrite':
                // Memoria conversazionale: il backend ha riscritto la
                // domanda per il retrieval. Trace + meta per renderlo
                // visibile nel pannello "Dettagli" del messaggio.
                return {
                  ...m,
                  trace: [
                    ...(m.trace ?? []),
                    { step: `Query riscritta: «${ev.rewritten}»`, at: now },
                  ],
                  queryRewrite: { original: ev.original, rewritten: ev.rewritten },
                };
              case 'citation_warning':
                return {
                  ...m,
                  citationWarning: { summary: ev.summary, violations: ev.violations },
                };
              case 'error':
                return { ...m, error: ev.message, streaming: false, completedAt: now };
              default:
                return m;
            }
          })
        );
      };

      // Auto-retry su errori di rete transitori quando nessun token è ancora
      // arrivato. Max 2 tentativi totali (1 retry), backoff breve per non
      // allungare l'attesa utente. Skip se abort.
      let firstTokenSeen = false;
      const onEventTracked = (ev: StreamEvent) => {
        if (ev.type === 'token') firstTokenSeen = true;
        onEvent(ev);
      };
      const isTransient = (e: unknown) => {
        const err = e as Error;
        if (!err) return false;
        if (err.name === 'AbortError') return false;
        const msg = err.message ?? '';
        return /failed to fetch|network|ECONNRESET|socket|stream error 5\d\d|stream error 429/i.test(
          msg
        );
      };

      let attempt = 0;
      const MAX_ATTEMPTS = 2;
      let lastErr: unknown = null;
      while (attempt < MAX_ATTEMPTS) {
        attempt += 1;
        try {
          await streamChat(trimmed, historyForBackend, onEventTracked, {
            signal: ctrl.signal,
            graph: opts.graph,
            limit: opts.limit,
            conversationId:
              opts.conversationIdRef?.current ?? opts.conversationId ?? null,
          });
          lastErr = null;
          break;
        } catch (err) {
          lastErr = err;
          if (ctrl.signal.aborted || !isTransient(err) || firstTokenSeen) break;
          // jitter 400–900ms, solo se resta un tentativo
          if (attempt < MAX_ATTEMPTS) {
            await new Promise((r) => setTimeout(r, 400 + Math.random() * 500));
          }
        }
      }

      const now = Date.now();
      if (lastErr) {
        if ((lastErr as Error).name === 'AbortError') {
          setMessages((prev) =>
            prev.map((m) => (m.id === asstId ? { ...m, streaming: false, completedAt: now } : m))
          );
        } else {
          const msg = (lastErr as Error).message ?? 'errore sconosciuto';
          setLastError(msg);
          setMessages((prev) =>
            prev.map((m) =>
              m.id === asstId ? { ...m, streaming: false, error: msg, completedAt: now } : m
            )
          );
        }
      }
      // Ownership guard: il `done` event ha già flippato isStreaming=false e
      // (potenzialmente) l'utente ha avviato un nuovo send con il proprio
      // AbortController. Solo il send "owner" del ctrl corrente può
      // ripulire lo state — altrimenti il vecchio stream (che continua a
      // consumare warnings post-done) chiuderebbe la UI del nuovo.
      if (abortRef.current === ctrl) {
        setIsStreaming(false);
        abortRef.current = null;
      }
    },
    [
      isStreaming,
      messages,
      opts.graph,
      opts.limit,
      opts.conversationId,
      opts.onConversationId,
      opts.onAssistantMessageId,
    ]
  );

  const stop = useCallback(() => {
    abortRef.current?.abort();
  }, []);

  const reset = useCallback(() => {
    abortRef.current?.abort();
    setMessages([]);
    setLastError(null);
  }, []);

  /**
   * Rigenera l'ultima risposta assistant: rimuove assistant + user più recenti,
   * poi ri-invia l'ultimo prompt. No-op se streaming attivo o nessun turno utente.
   *
   * Multi-tenancy (Fase 6.1): se `conversationIdRef.current` è valorizzato
   * (utente loggato), allinea il server troncando i turni rimossi —
   * altrimenti il prossimo `latest_turns` re-inietta gli orfani nel context.
   */
  const regenerate = useCallback(async () => {
    if (isStreaming) return;
    let lastUserIdx = -1;
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === 'user') {
        lastUserIdx = i;
        break;
      }
    }
    if (lastUserIdx < 0) return;
    const lastUserMsg = messages[lastUserIdx];
    const lastUserContent = lastUserMsg.content;

    // Sync server: tronca dal turno user incluso (server-side è già
    // persistito; senza truncate il prossimo turno duplica la history).
    const convId = opts.conversationIdRef?.current ?? opts.conversationId ?? null;
    if (convId && lastUserMsg.id) {
      try {
        await truncateMessagesFrom(convId, lastUserMsg.id);
      } catch (err) {
        console.warn('[useChat] regenerate: truncate server failed', err);
      }
    }

    setMessages((prev) => prev.slice(0, lastUserIdx));
    setTimeout(() => {
      void send(lastUserContent);
    }, 0);
  }, [isStreaming, messages, send, opts.conversationIdRef, opts.conversationId]);

  /**
   * Modifica un messaggio utente esistente e ri-genera la risposta.
   * Tronca tutti i messaggi dopo quello edit (incluso assistant risposta)
   * e re-invia con il nuovo contenuto.
   *
   * Backend sync (Fase 6.1): truncate server da `messageId` incluso, così
   * il vecchio prompt + risposta non finiscono nel `latest_turns` del
   * prossimo /api/chat/stream.
   */
  const editAndResend = useCallback(
    async (messageId: string, content: string) => {
      if (isStreaming) return;
      const trimmed = content.trim();
      if (!trimmed) return;
      const idx = messages.findIndex((m) => m.id === messageId && m.role === 'user');
      if (idx < 0) return;

      const convId = opts.conversationIdRef?.current ?? opts.conversationId ?? null;
      if (convId) {
        try {
          await truncateMessagesFrom(convId, messageId);
        } catch (err) {
          console.warn('[useChat] editAndResend: truncate server failed', err);
        }
      }

      setMessages((prev) => prev.slice(0, idx));
      setTimeout(() => {
        void send(trimmed);
      }, 0);
    },
    [isStreaming, messages, send, opts.conversationIdRef, opts.conversationId]
  );

  return {
    messages,
    isStreaming,
    lastError,
    send,
    regenerate,
    editAndResend,
    stop,
    reset,
    setMessages,
  };
}
