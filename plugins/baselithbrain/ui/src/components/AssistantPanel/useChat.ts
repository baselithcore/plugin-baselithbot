import { useEffect, useRef, useState } from 'react';
import { useBrain } from '@/store';
import { api } from '@/lib/api';
import type { TransformResult } from '@/lib/types';
import { toMsg, type Msg } from './types';

/** Chat engine for the assistant: owns the live turn list + streaming + actions.
 *
 * Conversational memory lives on the server. This hook loads a thread's turns
 * when the active thread changes, streams new answers, and lets the server
 * persist the exchange (it returns the thread id via a ``meta`` event when a new
 * thread is opened on the first turn).
 */
export function useChat() {
  const activeConversationId = useBrain((s) => s.activeConversationId);
  const setActiveConversation = useBrain((s) => s.setActiveConversation);
  const loadConversations = useBrain((s) => s.loadConversations);
  const workspace = useBrain((s) => s.activeWorkspace);
  const active = useBrain((s) => s.active);
  const applyServerNote = useBrain((s) => s.applyServerNote);

  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [busy, setBusy] = useState(false);
  const [loadingThread, setLoadingThread] = useState(false);
  const abort = useRef<AbortController | null>(null);
  //: A thread id whose turns are already live (just streamed) — skip its fetch.
  const skipFetch = useRef<string | null>(null);

  // Hydrate the turn list whenever the active thread changes (or clears).
  useEffect(() => {
    if (!activeConversationId) {
      setMsgs([]);
      return;
    }
    if (skipFetch.current === activeConversationId) {
      skipFetch.current = null;
      return;
    }
    let cancelled = false;
    setLoadingThread(true);
    api
      .getConversation(activeConversationId)
      .then((c) => {
        if (!cancelled) setMsgs(c.messages.map(toMsg));
      })
      .catch(() => {
        if (!cancelled) setMsgs([]);
      })
      .finally(() => {
        if (!cancelled) setLoadingThread(false);
      });
    return () => {
      cancelled = true;
    };
  }, [activeConversationId]);

  const pushAssistant = (text: string, suggestions?: string[]) =>
    setMsgs((m) => [...m, { role: 'assistant', text, suggestions }]);

  const send = async (raw: string) => {
    const q = raw.trim();
    if (!q || busy) return;
    setMsgs((m) => [...m, { role: 'user', text: q }, { role: 'assistant', text: '' }]);
    setBusy(true);
    abort.current = new AbortController();
    let createdId: string | null = null;
    try {
      await api.aiChat(
        q,
        { conversationId: activeConversationId, workspace },
        (e) =>
          setMsgs((m) => {
            const copy = [...m];
            const last = copy[copy.length - 1];
            if (e.type === 'meta') createdId = e.conversation_id;
            else if (e.type === 'token') last.text += e.text;
            else if (e.type === 'sources') last.sources = e.sources;
            else if (e.type === 'groundedness')
              last.grounding = { score: e.score, level: e.level, feedback: e.feedback };
            else if (e.type === 'error') last.text = `⚠️ ${e.message}`;
            return copy;
          }),
        abort.current.signal
      );
    } catch {
      /* aborted or network error — already reflected in the bubble */
    } finally {
      setBusy(false);
      // Adopt a freshly opened thread id without re-fetching (turns already live).
      if (createdId && createdId !== activeConversationId) {
        skipFetch.current = createdId;
        setActiveConversation(createdId);
      }
      void loadConversations();
    }
  };

  const research = async (raw: string) => {
    const q = raw.trim();
    if (!q || busy) return;
    setMsgs((m) => [...m, { role: 'user', text: q }, { role: 'assistant', text: '' }]);
    setBusy(true);
    abort.current = new AbortController();
    try {
      const r = await api.aiResearch(q, abort.current.signal);
      setMsgs((m) => {
        const copy = [...m];
        const last = copy[copy.length - 1];
        last.text = r.answer || 'No conclusion reached.';
        last.sources = r.sources.map((s, i) => ({ n: i + 1, id: s.id, title: s.title }));
        last.trace = r.trace;
        return copy;
      });
    } catch (e) {
      setMsgs((m) => {
        const copy = [...m];
        copy[copy.length - 1].text = `⚠️ ${(e as Error).message}`;
        return copy;
      });
    } finally {
      setBusy(false);
    }
  };

  const stop = () => {
    abort.current?.abort();
    setBusy(false);
  };

  const newChat = () => {
    if (busy) return;
    setActiveConversation(null);
    setMsgs([]);
  };

  const runAction = async (action: string) => {
    if (busy) return;
    if (!active) {
      pushAssistant('Open a note first.');
      return;
    }
    setBusy(true);
    try {
      const note = await api.getNote(active.id);
      if (!note.body.trim()) {
        pushAssistant(`“${note.title}” is empty — write something first.`);
        return;
      }
      const r: TransformResult = await api.aiTransform(action, note.body, note.title);
      if (action === 'autotag' && r.tags?.length) {
        const saved = await api.updateNote(active.id, { tags: r.tags });
        applyServerNote(saved);
        pushAssistant(`Applied tags: ${r.tags.map((t) => `\`#${t}\``).join(' ')}`);
      } else if (r.suggestions?.length) {
        pushAssistant('**Suggested links**', r.suggestions);
      } else if (r.result) {
        pushAssistant(r.result);
      } else {
        pushAssistant('No result.');
      }
    } catch (e) {
      pushAssistant(`⚠️ ${(e as Error).message}`);
    } finally {
      setBusy(false);
    }
  };

  return { msgs, busy, loadingThread, send, research, stop, newChat, runAction };
}
