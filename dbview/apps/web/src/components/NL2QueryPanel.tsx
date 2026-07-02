import { useCallback, useEffect, useRef, useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { AnimatePresence } from 'framer-motion';
import { Sparkles } from 'lucide-react';
import { toast } from 'sonner';
import {
  isIncompatibleOllamaModel,
  type Nl2QueryAskResponse,
  type Nl2SqlResponse,
} from '@dbview/shared';
import { api } from '../lib/api.js';
import { useAppStore } from '../store/app.js';
import { EmptyState } from './ui/EmptyState.js';
import { AssistantTurn } from './nl2query/AssistantTurn.js';
import { AssistantPanelHeader } from './nl2query/AssistantPanelHeader.js';
import { QueryComposer } from './nl2query/QueryComposer.js';
import { SuggestionsView } from './nl2query/SuggestionsView.js';
import { buildSuggestions } from './nl2query/suggestions.js';
import { buildHistoryPayload } from './nl2query/history-payload.js';
import type { ChatTurn, TurnMode } from './nl2query/turn-types.js';

let TURN_COUNTER = 0;
function newTurnId(): string {
  TURN_COUNTER += 1;
  return `t_${Date.now().toString(36)}_${TURN_COUNTER}`;
}

export function NL2QueryPanel() {
  const connId = useAppStore((s) => s.activeConnectionId);
  const provider = useAppStore((s) => s.provider);
  const setProvider = useAppStore((s) => s.setProvider);
  const model = useAppStore((s) => s.model);
  const setModel = useAppStore((s) => s.setModel);
  const conversation = useAppStore((s) => s.conversation);
  const addTurn = useAppStore((s) => s.addTurn);
  const updateTurn = useAppStore((s) => s.updateTurn);
  const clearConversation = useAppStore((s) => s.clearConversation);
  const setLastResponse = useAppStore((s) => s.setLastResponse);
  const autoExecute = useAppStore((s) => s.autoExecute);
  const setAutoExecute = useAppStore((s) => s.setAutoExecute);
  const setRightCollapsed = useAppStore((s) => s.setRightCollapsed);
  const responseLocale = useAppStore((s) => s.responseLocale);

  const [prompt, setPrompt] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const schemaQuery = useQuery({
    queryKey: ['schema', connId],
    queryFn: () => api.getSchema(connId!),
    enabled: !!connId,
  });
  const suggestions = buildSuggestions(schemaQuery.data);

  useEffect(() => {
    if (provider === 'ollama' && model && isIncompatibleOllamaModel(model)) {
      setModel(undefined);
    }
  }, [provider, model, setModel]);

  // Auto-scroll on new turn / status change.
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
  }, [conversation]);

  const submit = useMutation({
    mutationFn: async (input: {
      mode: TurnMode;
      turnId: string;
      prompt: string;
      history: ReturnType<typeof buildHistoryPayload>;
    }) => {
      const { mode, turnId, prompt: text, history } = input;
      if (mode === 'ask') {
        updateTurn(turnId, { status: 'translating' });
        // Visual hint: stage flips while we await the single round-trip.
        const stageTimer = setTimeout(() => updateTurn(turnId, { status: 'executing' }), 900);
        try {
          const r: Nl2QueryAskResponse = await api.ask({
            connectionId: connId!,
            prompt: text,
            provider,
            model,
            rowLimit: 100,
            locale: responseLocale,
            history,
          });
          clearTimeout(stageTimer);
          updateTurn(turnId, {
            status: 'ready',
            translation: r.translation,
            result: r.result ?? undefined,
            executionError: r.executionError ?? undefined,
            summary: r.summary,
            highlights: r.highlights,
            followUps: r.followUps,
            totalDurationMs: r.totalDurationMs,
          });
          setLastResponse(r.translation);
          if (r.translation.warnings.some((w) => w.severity === 'warn')) {
            toast.warning('Query generated with warnings');
          }
          return r;
        } catch (err) {
          clearTimeout(stageTimer);
          throw err;
        }
      } else {
        updateTurn(turnId, { status: 'translating' });
        const t: Nl2SqlResponse = await api.translate({
          connectionId: connId!,
          prompt: text,
          provider,
          model,
          allowDml: false,
          rowLimit: 100,
          locale: responseLocale,
          history,
        });
        updateTurn(turnId, { status: 'ready', translation: t });
        setLastResponse(t);
        if (t.warnings.some((w) => w.severity === 'warn')) {
          toast.warning('Query generated with warnings');
        }
        return t;
      }
    },
    onError: (err: Error, vars) => {
      updateTurn(vars.turnId, { status: 'error', error: err.message });
      // In-card error block carries the full detail. Toast is just an audible cue.
      toast.error('Generation failed');
    },
  });

  const sendPrompt = useCallback(
    (text: string, overrideMode?: TurnMode) => {
      const trimmed = text.trim();
      if (!connId || !trimmed || submit.isPending) return;
      const mode: TurnMode = overrideMode ?? (autoExecute ? 'ask' : 'translate');
      // Snapshot the conversation BEFORE adding the new turn so the LLM sees
      // prior context but not the placeholder for the request in flight.
      const history = buildHistoryPayload(conversation);
      const turnId = newTurnId();
      const turn: ChatTurn = {
        id: turnId,
        prompt: trimmed,
        mode,
        status: 'pending',
        createdAt: Date.now(),
      };
      addTurn(turn);
      submit.mutate({ mode, turnId, prompt: trimmed, history });
    },
    [connId, submit, autoExecute, addTurn, conversation],
  );

  const send = useCallback(
    (overrideMode?: TurnMode) => {
      sendPrompt(prompt, overrideMode);
      setPrompt('');
    },
    [sendPrompt, prompt],
  );

  const retry = useCallback(
    (turnPrompt: string) => {
      sendPrompt(turnPrompt);
    },
    [sendPrompt],
  );

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
        if (document.activeElement === textareaRef.current && prompt.trim()) {
          send();
        }
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [prompt, send]);

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey && !e.metaKey && !e.ctrlKey) {
        e.preventDefault();
        send();
      }
    },
    [send],
  );

  if (!connId) {
    return (
      <div data-tour="nl2query-panel" className="panel h-full">
        <EmptyState
          icon={<Sparkles className="w-5 h-5" />}
          title="Ask in natural language"
          description="Connect a database and ask questions in plain English. dbview drafts a safe query, runs it, and answers in plain language."
        />
      </div>
    );
  }

  return (
    <div data-tour="nl2query-panel" className="flex flex-col h-full min-h-0 panel overflow-hidden">
      <AssistantPanelHeader
        schema={schemaQuery.data}
        schemaLoading={schemaQuery.isLoading}
        conversationCount={conversation.length}
        onClear={() => {
          clearConversation();
          setLastResponse(null);
        }}
        onCollapse={() => setRightCollapsed(true)}
      />

      <div ref={scrollRef} className="flex-1 min-h-0 overflow-auto p-3 flex flex-col gap-3">
        {conversation.length === 0 ? (
          <SuggestionsView
            onPick={setPrompt}
            suggestions={suggestions}
            schema={schemaQuery.data}
            schemaLoading={schemaQuery.isLoading}
          />
        ) : (
          <AnimatePresence initial={false}>
            {conversation.map((turn) => (
              <AssistantTurn
                key={turn.id}
                turn={turn}
                connectionId={connId}
                onRetry={() => retry(turn.prompt)}
                onFollowUp={(q) => sendPrompt(q)}
              />
            ))}
          </AnimatePresence>
        )}
      </div>

      <QueryComposer
        prompt={prompt}
        provider={provider}
        model={model}
        autoExecute={autoExecute}
        busy={submit.isPending}
        textareaRef={textareaRef}
        onPromptChange={setPrompt}
        onProviderChange={setProvider}
        onModelChange={setModel}
        onAutoExecuteChange={setAutoExecute}
        onSend={send}
        onKeyDown={onKeyDown}
      />
    </div>
  );
}
