import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { Conversation, Message, Source } from '../lib/types';
import { uid } from '../lib/cn';
import {
  type ApiConversation,
  createConversation as apiCreate,
  deleteConversation as apiDelete,
  listConversations as apiList,
  listMessages as apiListMessages,
  updateConversation as apiUpdate,
} from '../lib/api/conversations';
import { toast } from 'sonner';

import { useAuth } from '../contexts/AuthContext';
import { migrateLegacyConversations } from '../lib/migrate-local-conversations';

const STORAGE_KEY = 'llm-wiki:conversations';

interface UseConversationsArgs {
  messages: Message[];
  setMessages: (m: Message[]) => void;
  isStreaming: boolean;
}

interface UseConversationsResult {
  conversations: Conversation[];
  activeId: string | null;
  active: Conversation | null;
  setActiveId: (id: string | null) => void;
  newChat: () => Promise<string>;
  rename: (id: string, title: string) => Promise<void>;
  togglePin: (id: string) => Promise<void>;
  remove: (id: string) => Promise<void>;
  /** notifica al hook che il backend ha creato/cambiato conversation_id (da useChat) */
  attachServerConversationId: (id: string) => void;
}

/**
 * Hook conversation state — Fase 6 multi-tenancy.
 *
 * Backend-first quando l'utente è loggato (Postgres ON):
 * - Source of truth = backend (RLS-isolato per tenant).
 * - Cache locale (state React) ottimistica per UX fluida.
 * - localStorage ancora usato come **fallback completo** quando l'utente
 *   è anonimo (chat legacy stateless senza Postgres). Le due modalità
 *   non si toccano: chiavi storage diverse a seconda di `user_id`.
 *
 * Convergenza con server: ad ogni rename/pin/delete invochiamo l'API,
 * mostriamo update ottimistico, rollback su errore.
 */
export function useConversations({
  messages,
  setMessages,
  isStreaming,
}: UseConversationsArgs): UseConversationsResult {
  const { user } = useAuth();
  const userKey = user ? `${STORAGE_KEY}:user:${user.id}` : STORAGE_KEY;
  const isAuthenticated = !!user;

  const [conversations, setConversations] = useState<Conversation[]>(() => {
    if (isAuthenticated) return []; // hydrated da fetch sotto
    try {
      const raw = localStorage.getItem(userKey);
      return raw ? (JSON.parse(raw) as Conversation[]) : [];
    } catch {
      return [];
    }
  });
  const [activeId, setActiveIdState] = useState<string | null>(null);
  const messagesLoadedFor = useRef<string | null>(null);

  const active = useMemo(
    () => conversations.find((c) => c.id === activeId) ?? null,
    [conversations, activeId]
  );

  // --- bootstrap quando user cambia ----------------------------------------

  useEffect(() => {
    let cancelled = false;
    if (!isAuthenticated) {
      // Carica da localStorage
      try {
        const raw = localStorage.getItem(userKey);
        const parsed = raw ? (JSON.parse(raw) as Conversation[]) : [];
        if (!cancelled) {
          setConversations(parsed);
          setActiveIdState(parsed[0]?.id ?? null);
        }
      } catch {
        /* ignore */
      }
      return;
    }
    // Loggato: prima migration legacy localStorage → backend (se applicabile),
    // poi fetch lista. Migration è idempotente via flag dedicato — re-mount
    // non rifa l'import.
    (async () => {
      try {
        const userId = user!.id;
        const migrated = await migrateLegacyConversations(userId);
        if (!migrated.skipped && migrated.conversations_imported > 0) {
          const errCount = migrated.errors.length;
          const detail =
            `${migrated.conversations_imported} conversazion${
              migrated.conversations_imported === 1 ? 'e' : 'i'
            } · ${migrated.messages_imported} messaggi`;
          if (errCount > 0) {
            toast.warning('Cronologia importata parzialmente', {
              description: `${detail}. ${errCount} errori — vedi console.`,
            });
            // eslint-disable-next-line no-console
            console.warn('[useConversations] migration errors:', migrated.errors);
          } else {
            toast.success('Cronologia locale importata', { description: detail });
          }
        } else if (migrated.errors.length > 0) {
          // Skipped/0-imported ma con errori: solo console (no toast spam).
          // eslint-disable-next-line no-console
          console.warn('[useConversations] migration errors:', migrated.errors);
        }
        const list = await apiList();
        if (cancelled) return;
        const conv = list.map(_apiToLocal);
        setConversations(conv);
        // Deep-link ``?conversation=<uuid>``: usato dall'admin
        // feedback page per saltare alla conversation origine di un
        // record. Validato contro la lista corrente (evita selectare
        // un id arrivato da altro tenant / cancellato). URL ripulito
        // dopo per evitare re-trigger su navigation.
        const params = new URLSearchParams(window.location.search);
        const targetId = params.get('conversation');
        const targetExists = targetId && conv.some((c) => c.id === targetId);
        setActiveIdState(targetExists ? targetId : (conv[0]?.id ?? null));
        if (targetExists) {
          params.delete('conversation');
          const search = params.toString();
          const url = window.location.pathname + (search ? '?' + search : '');
          window.history.replaceState({}, '', url);
        }
      } catch (err) {
        // eslint-disable-next-line no-console
        console.warn('[useConversations] fetch list failed', err);
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isAuthenticated, user?.id]);

  // --- carica messaggi server quando cambia conversation attiva ------------

  useEffect(() => {
    if (!isAuthenticated || !activeId) return;
    if (messagesLoadedFor.current === activeId) {
      // già caricati — restore da cache locale
      const cached = conversations.find((c) => c.id === activeId);
      if (cached) setMessages(cached.messages);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const apiMsgs = await apiListMessages(activeId, { limit: 500 });
        if (cancelled) return;
        const localMsgs: Message[] = apiMsgs.map(_apiMessageToLocal);
        setMessages(localMsgs);
        // Cache nel state React
        setConversations((prev) =>
          prev.map((c) => (c.id === activeId ? { ...c, messages: localMsgs } : c))
        );
        messagesLoadedFor.current = activeId;
      } catch (err) {
        // eslint-disable-next-line no-console
        console.warn('[useConversations] fetch messages failed', err);
        setMessages([]);
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeId, isAuthenticated]);

  // --- carica messaggi quando NON loggato (legacy localStorage) ------------

  useEffect(() => {
    if (isAuthenticated) return;
    if (!active) return;
    setMessages(active.messages);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeId]);

  // --- persisti modifiche local-side (cache state in conversations) --------

  useEffect(() => {
    if (!activeId) return;
    setConversations((prev) =>
      prev.map((c) =>
        c.id === activeId
          ? {
              ...c,
              messages,
              title: c.titleLocked ? c.title : (deriveTitle(messages) ?? c.title),
              updatedAt: Date.now(),
            }
          : c
      )
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages]);

  // --- localStorage sync solo per modalità anonima -------------------------

  useEffect(() => {
    if (isAuthenticated) return;
    try {
      localStorage.setItem(userKey, JSON.stringify(conversations));
    } catch {
      /* ignore quota */
    }
  }, [conversations, isAuthenticated, userKey]);

  useEffect(() => {
    if (isAuthenticated) return;
    const handler = (e: StorageEvent) => {
      if (e.key !== userKey || e.newValue === null) return;
      if (isStreaming) return;
      try {
        const next = JSON.parse(e.newValue) as Conversation[];
        setConversations(next);
        if (activeId) {
          const found = next.find((c) => c.id === activeId);
          if (found) setMessages(found.messages);
        }
      } catch {
        /* ignore malformed */
      }
    };
    window.addEventListener('storage', handler);
    return () => window.removeEventListener('storage', handler);
  }, [isStreaming, activeId, setMessages, isAuthenticated, userKey]);

  // --- mutations -----------------------------------------------------------

  const setActiveId = useCallback((id: string | null) => {
    setActiveIdState(id);
  }, []);

  const newChat = useCallback(async (): Promise<string> => {
    const localId = uid();
    const tempConv: Conversation = {
      id: localId,
      title: 'Nuova conversazione',
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
    setConversations((p) => [tempConv, ...p]);
    setActiveIdState(localId);
    setMessages([]);
    if (!isAuthenticated) return localId;

    // Loggato: crea su backend, swap id locale → id server.
    try {
      const created = await apiCreate('Nuova conversazione');
      setConversations((prev) =>
        prev.map((c) => (c.id === localId ? { ..._apiToLocal(created), messages: [] } : c))
      );
      setActiveIdState(created.id);
      return created.id;
    } catch (err) {
      console.warn('[useConversations] create failed (resta locale)', err);
      return localId;
    }
  }, [isAuthenticated, setMessages]);

  const rename = useCallback(
    async (id: string, title: string) => {
      const prevTitle = conversations.find((c) => c.id === id)?.title;
      setConversations((prev) =>
        prev.map((c) => (c.id === id ? { ...c, title, titleLocked: true } : c))
      );
      if (!isAuthenticated) return;
      try {
        await apiUpdate(id, { title, title_locked: true });
      } catch (err) {
        console.warn('[useConversations] rename failed, rollback', err);
        setConversations((prev) =>
          prev.map((c) =>
            c.id === id ? { ...c, title: prevTitle ?? c.title, titleLocked: false } : c
          )
        );
      }
    },
    [conversations, isAuthenticated]
  );

  const togglePin = useCallback(
    async (id: string) => {
      const prevPinned = conversations.find((c) => c.id === id)?.pinned;
      const nextPinned = !prevPinned;
      setConversations((prev) =>
        prev.map((c) => (c.id === id ? { ...c, pinned: nextPinned } : c))
      );
      if (!isAuthenticated) return;
      try {
        await apiUpdate(id, { pinned: nextPinned });
      } catch (err) {
        console.warn('[useConversations] togglePin failed, rollback', err);
        setConversations((prev) =>
          prev.map((c) => (c.id === id ? { ...c, pinned: prevPinned ?? false } : c))
        );
      }
    },
    [conversations, isAuthenticated]
  );

  const remove = useCallback(
    async (id: string) => {
      const snapshot = conversations;
      setConversations((prev) => {
        const next = prev.filter((c) => c.id !== id);
        if (activeId === id) {
          const nextActive = next[0]?.id ?? null;
          setActiveIdState(nextActive);
          setMessages(next.find((c) => c.id === nextActive)?.messages ?? []);
        }
        return next;
      });
      if (!isAuthenticated) return;
      try {
        await apiDelete(id);
      } catch (err) {
        console.warn('[useConversations] delete failed, rollback', err);
        setConversations(snapshot);
      }
    },
    [conversations, activeId, setMessages, isAuthenticated]
  );

  const attachServerConversationId = useCallback(
    (serverId: string) => {
      // useChat chiama questo quando il backend autocrea una conversation
      // (primo turno con activeId locale). Swap id locale → server.
      if (!activeId || activeId === serverId) return;
      const localId = activeId;
      setConversations((prev) =>
        prev.map((c) => (c.id === localId ? { ...c, id: serverId } : c))
      );
      setActiveIdState(serverId);
      messagesLoadedFor.current = serverId;
    },
    [activeId]
  );

  return {
    conversations,
    activeId,
    active,
    setActiveId,
    newChat,
    rename,
    togglePin,
    remove,
    attachServerConversationId,
  };
}

// --- helpers ----------------------------------------------------------------

function deriveTitle(messages: Message[]): string | null {
  const first = messages.find((m) => m.role === 'user');
  if (!first) return null;
  const text = first.content.replace(/\s+/g, ' ').trim();
  return text.slice(0, 48) + (text.length > 48 ? '…' : '');
}

function _apiToLocal(c: ApiConversation): Conversation {
  return {
    id: c.id,
    title: c.title,
    messages: [],
    createdAt: Date.parse(c.created_at) || Date.now(),
    updatedAt: Date.parse(c.updated_at) || Date.now(),
    titleLocked: c.title_locked,
    pinned: c.pinned,
  };
}

function _apiMessageToLocal(m: {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  sources?: unknown[] | null;
  created_at: string;
}): Message {
  // 'system' role non è in Role; mappiamo a 'assistant' per safety.
  const role = m.role === 'system' ? 'assistant' : m.role;
  return {
    id: m.id,
    role,
    content: m.content,
    sources: (m.sources as Source[] | undefined) ?? undefined,
    createdAt: Date.parse(m.created_at) || Date.now(),
  };
}
