import { FormEvent, useCallback, useEffect, useRef, useState } from 'react';

import { sendChatStream } from '../../api/client';
import {
  ChatAction,
  ChatAgentStatus,
  ChatMessage,
  ChatResponsePayload,
  ChatSource,
  ChatStreamEvent,
  JiraIssue,
} from '../../types';

const newSessionId = () =>
  typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : Math.random().toString(16).slice(2);

export const examplePrompts = [
  'Elenca i file più aggiornati relativi alla roadmap',
  'Quali rischi hai identificato per la release corrente?',
  'Genera un project plan per migliorare la parte di onboarding',
];

const JIRA_AGENT_STEPS = [
  { key: 'classification', label: 'Analisi richiesta' },
  { key: 'context', label: 'Contesto progetto' },
  { key: 'planning', label: 'Generazione storie' },
  { key: 'sync', label: 'Creazione su Jira' },
] as const;

const JIRA_STEP_KEYS = new Set(JIRA_AGENT_STEPS.map((step) => step.key));

const normalizeJiraStep = (step?: string | null) => {
  if (!step) return null;
  if (step === 'jira_sync') return 'sync';
  return JIRA_STEP_KEYS.has(step as (typeof JIRA_AGENT_STEPS)[number]['key']) ? step : null;
};

const isJiraAgentEvent = (event: ChatStreamEvent) =>
  event.event_type === 'status' &&
  (event.agent === 'jira' || Boolean(normalizeJiraStep(event.step)));

const buildJiraAgentStatus = (
  activeStep: string | null,
  detail: string,
  state: ChatAgentStatus['state'],
  summary?: string
): ChatAgentStatus => {
  const activeIndex =
    activeStep === null ? -1 : JIRA_AGENT_STEPS.findIndex((step) => step.key === activeStep);
  const completed = state === 'completed';

  return {
    agent: 'jira',
    title:
      state === 'completed'
        ? 'Creazione Jira completata'
        : state === 'blocked'
          ? 'Creazione Jira in attesa'
          : 'Creazione backlog su Jira',
    detail,
    state,
    summary,
    steps: JIRA_AGENT_STEPS.map((step, index) => ({
      key: step.key,
      label: step.label,
      state:
        completed || index < activeIndex
          ? 'completed'
          : index === activeIndex
            ? 'active'
            : 'pending',
    })),
  };
};

const buildJiraAgentMessage = (
  activeStep: string | null,
  detail: string,
  state: ChatAgentStatus['state'],
  summary?: string
): ChatMessage => ({
  role: 'assistant',
  kind: 'agent-status',
  text: detail,
  agentStatus: buildJiraAgentStatus(activeStep, detail, state, summary),
});

const summarizeJiraCreation = (issues: JiraIssue[]) => {
  const created = issues.filter((issue) => issue.key && !issue.error).length;
  const failed = issues.filter((issue) => issue.error).length;
  if (created > 0 && failed > 0) {
    return `${created} ticket creati, ${failed} con errore.`;
  }
  if (created > 0) {
    return `${created} ticket creati su Jira.`;
  }
  if (failed > 0) {
    return `${failed} ticket non creati su Jira.`;
  }
  return 'Elaborazione Jira completata.';
};

type UseChatPanelResult = {
  messages: ChatMessage[];
  conversationId: string;
  setConversationId: (value: string) => void;
  input: string;
  setInput: (value: string) => void;
  loading: boolean;
  generationStartTime: number | null;
  sources: ChatSource[];
  jiraIssues: JiraIssue[];
  jiraExpanded: boolean;
  setJiraExpanded: (value: boolean) => void;
  error: string | null;
  copied: boolean;
  handleSend: (evt?: FormEvent) => Promise<void>;
  handleActionClick: (action: ChatAction) => Promise<void>;
  resetConversation: () => void;
  copyConversationId: () => Promise<void>;
};

export const useChatPanel = (): UseChatPanelResult => {
  const [conversationId, setConversationId] = useState<string>(() => {
    if (typeof window === 'undefined') return newSessionId();
    return sessionStorage.getItem('console:conversation-id') || newSessionId();
  });
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    if (typeof window === 'undefined') return [];
    try {
      const stored = sessionStorage.getItem('console:messages');
      return stored ? JSON.parse(stored) : [];
    } catch (e) {
      console.warn('Failed to parse stored messages', e);
      return [];
    }
  });
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [generationStartTime, setGenerationStartTime] = useState<number | null>(null);
  const [sources, setSources] = useState<ChatSource[]>(() => {
    if (typeof window === 'undefined') return [];
    try {
      const stored = sessionStorage.getItem('console:sources');
      return stored ? JSON.parse(stored) : [];
    } catch (e) {
      return [];
    }
  });
  const [jiraIssues, setJiraIssues] = useState<JiraIssue[]>(() => {
    if (typeof window === 'undefined') return [];
    try {
      const stored = sessionStorage.getItem('console:jira-issues');
      return stored ? JSON.parse(stored) : [];
    } catch (e) {
      return [];
    }
  });
  const [jiraExpanded, setJiraExpanded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [docContext, setDocContext] = useState<string | null>(() => {
    if (typeof window === 'undefined') return null;
    return sessionStorage.getItem('console:last-doc-id');
  });
  const prevDocRef = useRef<string | null>(docContext);

  const resetConversation = useCallback(() => {
    setMessages([]);
    setSources([]);
    setJiraIssues([]);
    setJiraExpanded(false);
    const newId = newSessionId();
    setConversationId(newId);
    setCopied(false);
    if (typeof window !== 'undefined') {
      sessionStorage.removeItem('console:messages');
      sessionStorage.removeItem('console:sources');
      sessionStorage.removeItem('console:jira-issues');
      sessionStorage.setItem('console:conversation-id', newId);
    }
  }, []);

  useEffect(() => {
    const onDocUpdate = (event: Event) => {
      const detail = (event as CustomEvent<string>).detail;
      const next =
        detail ||
        (typeof window !== 'undefined' ? sessionStorage.getItem('console:last-doc-id') : null);
      setDocContext(next || null);
    };
    window.addEventListener('console:last-doc-updated', onDocUpdate);
    return () => window.removeEventListener('console:last-doc-updated', onDocUpdate);
  }, []);

  useEffect(() => {
    if (prevDocRef.current && docContext && prevDocRef.current !== docContext) {
      resetConversation();
    }
    prevDocRef.current = docContext || null;
  }, [docContext, resetConversation]);

  const processQuery = async (queryText: string) => {
    if (!queryText || loading) return;

    const nextMessages: ChatMessage[] = [
      ...messages,
      { role: 'user', text: queryText } as ChatMessage,
    ];
    setMessages(nextMessages);
    setInput('');
    setError(null);
    setLoading(true);
    setGenerationStartTime(Date.now());

    let kbLabel: string | undefined;
    if (docContext && typeof window !== 'undefined') {
      try {
        const cached = sessionStorage.getItem(`console:analysis-cache:${docContext}`);
        if (cached) {
          const parsed = JSON.parse(cached);
          kbLabel = parsed.kb?.label || parsed.metadata?.kb_label;
        }
      } catch (e) {
        console.warn('Error reading analysis cache for label', e);
      }
    }

    try {
      const requestStartTime = Date.now();
      let accumulatedText = '';
      let jiraStatusStep: string | null = null;
      let jiraStatusDetail = '';
      let jiraStatusVisible = false;

      const buildMessages = (
        answerText = '',
        actions?: ChatAction[],
        statusState: ChatAgentStatus['state'] = 'running',
        summary?: string,
        duration?: number
      ) => {
        const updatedMessages = [...nextMessages];
        if (jiraStatusVisible) {
          updatedMessages.push(
            buildJiraAgentMessage(
              jiraStatusStep,
              jiraStatusDetail || 'Creazione Jira in corso...',
              statusState,
              summary
            )
          );
        }
        if (answerText) {
          updatedMessages.push({
            role: 'assistant',
            text: answerText,
            actions,
            duration,
          } as ChatMessage);
        }
        return updatedMessages;
      };

      const payload: ChatResponsePayload = await sendChatStream(
        queryText,
        conversationId,
        kbLabel,
        (chunk: string) => {
          accumulatedText += chunk;
          setMessages(buildMessages(accumulatedText));
        },
        (event: ChatStreamEvent) => {
          if (event.event_type !== 'status' || !isJiraAgentEvent(event)) return;
          const statusEvent = event;
          jiraStatusVisible = true;
          jiraStatusStep = normalizeJiraStep(statusEvent.step) || jiraStatusStep;
          jiraStatusDetail =
            statusEvent.message || jiraStatusDetail || 'Creazione Jira in corso...';
          setMessages(buildMessages(accumulatedText, undefined, 'running'));
        }
      );

      const answer = payload.answer || accumulatedText || 'Nessuna risposta generata';
      const waitingForProject =
        jiraStatusVisible &&
        jiraStatusStep !== 'sync' &&
        Boolean(payload.suggested_actions?.length) &&
        !Boolean(payload.jira_issues?.some((issue) => issue.key));
      const finalStatusState: ChatAgentStatus['state'] = waitingForProject
        ? 'blocked'
        : 'completed';
      const jiraSummary = jiraStatusVisible
        ? waitingForProject
          ? 'Workflow in attesa della selezione del progetto Jira.'
          : summarizeJiraCreation(payload.created_jira_issues || [])
        : undefined;
      if (jiraStatusVisible) {
        jiraStatusDetail = waitingForProject
          ? jiraStatusDetail || 'Specifica il progetto Jira per continuare.'
          : jiraSummary || jiraStatusDetail || 'Creazione Jira completata.';
      }
      setMessages(
        buildMessages(
          answer,
          payload.suggested_actions,
          finalStatusState,
          jiraSummary,
          payload.duration ?? (Date.now() - requestStartTime) / 1000
        )
      );
      setSources(payload.sources || []);
      setJiraIssues(payload.jira_issues || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Errore inatteso');
      setMessages([
        ...nextMessages,
        { role: 'assistant', text: '⚠️ Errore durante la richiesta.' } as ChatMessage,
      ]);
    } finally {
      setLoading(false);
      setGenerationStartTime(null);
    }
  };

  const handleSend = async (evt?: FormEvent) => {
    evt?.preventDefault();
    await processQuery(input.trim());
  };

  const handleActionClick = async (action: ChatAction) => {
    await processQuery(action.payload);
  };

  const copyConversationId = async () => {
    try {
      await navigator.clipboard.writeText(conversationId);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setError('Impossibile copiare il Conversation ID.');
    }
  };

  useEffect(() => {
    if (typeof window === 'undefined') return;
    sessionStorage.setItem('console:conversation-id', conversationId);
  }, [conversationId]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    sessionStorage.setItem('console:messages', JSON.stringify(messages));
  }, [messages]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    sessionStorage.setItem('console:sources', JSON.stringify(sources));
  }, [sources]);

  useEffect(() => {
    if (typeof window === 'undefined') return;
    sessionStorage.setItem('console:jira-issues', JSON.stringify(jiraIssues));
  }, [jiraIssues]);

  useEffect(() => {
    setJiraExpanded(false);
  }, [jiraIssues]);

  return {
    messages,
    conversationId,
    setConversationId,
    input,
    setInput,
    loading,
    generationStartTime,
    sources,
    jiraIssues,
    jiraExpanded,
    setJiraExpanded,
    error,
    copied,
    handleSend,
    handleActionClick,
    resetConversation,
    copyConversationId,
  };
};
