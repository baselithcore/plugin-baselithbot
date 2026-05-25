import { useEffect, useRef, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import {
  Bot,
  Check,
  CheckCircle2,
  CircleAlert,
  Copy,
  LoaderCircle,
  MessageSquare,
  Sparkles,
  User,
} from 'lucide-react';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { ChatMessage, ChatAction } from '../../types';

type ChatWindowProps = {
  messages: ChatMessage[];
  onActionClick?: (action: ChatAction) => void;
  loading?: boolean;
  generationStartTime?: number | null;
};

const markdownComponents = {
  a: ({ node, ...props }: any) => <a {...props} target="_blank" rel="noopener noreferrer" />,
  table: ({ node, ...props }: any) => (
    <div className="markdown-table-wrapper">
      <table {...props} />
    </div>
  ),
};

function sanitizeMarkdown(text: string): string {
  return text
    .replace(
      /<\s*(script|style|iframe|object|embed|link|meta|base|form)\b[^>]*>[\s\S]*?<\s*\/\s*\1\s*>/gi,
      ''
    )
    .replace(/<\s*(script|style|iframe|object|embed|link|meta|base|form)\b[^>]*\/?\s*>/gi, '')
    .replace(/\son[a-z]+\s*=\s*(?:"[^"]*"|'[^']*'|[^\s>]+)/gi, '')
    .replace(/\s(href|src)\s*=\s*(["'])\s*javascript:[\s\S]*?\2/gi, ' $1="#"')
    .replace(/<br\s*\/?>/gi, '<br />');
}

const GenerationTimer = ({ startTime }: { startTime: number }) => {
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setElapsed((Date.now() - startTime) / 1000);
    }, 100);
    return () => clearInterval(interval);
  }, [startTime]);

  return (
    <span className="generation-time live" title="Generazione in corso...">
      <LoaderCircle size={10} className="spin" />
      Generando ({elapsed.toFixed(1)}s)
    </span>
  );
};

const ChatWindow = ({ messages, onActionClick, loading, generationStartTime }: ChatWindowProps) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null);
  const shouldAutoScrollRef = useRef(true);

  const normalizeText = (text: string) => text.replace(/<br\s*\/\?\s*>/gi, '\n');

  const handleCopy = async (text: string, idx: number) => {
    try {
      await navigator.clipboard.writeText(normalizeText(text));
      setCopiedIdx(idx);
      window.setTimeout(() => setCopiedIdx(null), 1400);
    } catch (err) {
      console.error('Copy failed', err);
    }
  };

  // Detect manual scroll
  const handleScroll = () => {
    if (!containerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = containerRef.current;
    // If user is within 50px of the bottom, enable auto-scroll
    const isAtBottom = scrollHeight - clientHeight - scrollTop < 50;
    shouldAutoScrollRef.current = isAtBottom;
  };

  // Auto-scroll logic
  useEffect(() => {
    const node = containerRef.current;
    if (!node) return;

    if (shouldAutoScrollRef.current) {
      node.scrollTo({
        top: node.scrollHeight,
        behavior: 'smooth',
      });
    }
  }, [messages, loading]);

  // Reset auto-scroll when a new generation starts (meaning user sent a message)
  useEffect(() => {
    if (loading && messages.length > 0 && messages[messages.length - 1].role === 'user') {
      shouldAutoScrollRef.current = true;
    }
  }, [loading, messages]);

  return (
    <div className="chat-window" aria-live="polite" ref={containerRef} onScroll={handleScroll}>
      <div className="chat-content-centered">
        {messages.map((msg, idx) => {
          const isAssistant = msg.role === 'assistant';
          const isCopied = copiedIdx === idx;
          const isAgentStatus = msg.kind === 'agent-status' && msg.agentStatus;
          const roleLabel = isAgentStatus ? 'Agent Jira' : isAssistant ? 'Agente' : 'Tu';
          const isLastMessage = idx === messages.length - 1;

          if (isAssistant && !isAgentStatus) {
            console.debug(`[ChatWindow] Message ${idx} duration:`, msg.duration);
          }

          return (
            <div
              key={idx}
              className={`message-row ${isAssistant ? 'assistant' : 'user'} ${isAgentStatus ? 'agent-status-row' : ''}`}
              data-bubble="true"
              data-role={msg.role}
              data-idx={idx}
              style={{ animationDelay: `${Math.min(idx * 0.05, 0.5)}s` }}
            >
              <div
                className={`bubble ${isAssistant ? 'assistant' : 'user'} ${isAgentStatus ? 'agent-status-bubble' : ''}`}
              >
                <div className="bubble-head">
                  <span
                    className={`role-chip ${isAssistant ? 'assistant' : 'user'} ${isAgentStatus ? 'agent' : ''}`}
                  >
                    {isAssistant ? (
                      <Bot size={12} strokeWidth={2.5} />
                    ) : (
                      <User size={12} strokeWidth={2.5} />
                    )}
                    {roleLabel}
                  </span>

                  {isAssistant && !isAgentStatus && (
                    <button
                      type="button"
                      className={`bubble-copy ${isCopied ? 'copied' : ''}`}
                      onClick={() => handleCopy(msg.text || '', idx)}
                      aria-label="Copia risposta dell'agente"
                      title={isCopied ? 'Copiato' : 'Copia'}
                    >
                      {isCopied ? <Check size={14} /> : <Copy size={14} />}
                    </button>
                  )}
                </div>

                {isAgentStatus && msg.agentStatus ? (
                  <div className="agent-status-card">
                    <div className="agent-status-title">
                      <span className={`agent-status-icon ${msg.agentStatus.state}`}>
                        {msg.agentStatus.state === 'completed' ? (
                          <CheckCircle2 size={16} />
                        ) : msg.agentStatus.state === 'blocked' ? (
                          <CircleAlert size={16} />
                        ) : (
                          <LoaderCircle size={16} className="spin" />
                        )}
                      </span>
                      <div>
                        <strong>{msg.agentStatus.title}</strong>
                        <p>{msg.agentStatus.detail}</p>
                      </div>
                    </div>
                    <div className="agent-status-steps">
                      {msg.agentStatus.steps.map((step) => (
                        <span key={step.key} className={`agent-step ${step.state}`}>
                          {step.state === 'completed' ? (
                            <Check size={12} />
                          ) : (
                            <Sparkles size={12} />
                          )}
                          {step.label}
                        </span>
                      ))}
                    </div>
                    {msg.agentStatus.summary && (
                      <p className="agent-status-summary">{msg.agentStatus.summary}</p>
                    )}
                  </div>
                ) : (
                  <ReactMarkdown
                    className="chat-markdown"
                    remarkPlugins={[remarkGfm]}
                    rehypePlugins={[rehypeRaw]}
                    components={markdownComponents}
                  >
                    {sanitizeMarkdown(msg.text || '')}
                  </ReactMarkdown>
                )}

                {isAssistant &&
                  !isAgentStatus &&
                  loading &&
                  isLastMessage &&
                  msg.duration === undefined && <span className="streaming-cursor" />}

                {isAssistant && !isAgentStatus && (
                  <div className="message-meta">
                    {msg.duration !== undefined ? (
                      <span className="generation-time" title="Tempo di risposta dell'agente">
                        <Sparkles size={10} />
                        Generato in {msg.duration.toFixed(1)}s
                      </span>
                    ) : (
                      isLastMessage &&
                      loading &&
                      generationStartTime && <GenerationTimer startTime={generationStartTime} />
                    )}
                  </div>
                )}

                {isAssistant && !isAgentStatus && msg.actions && msg.actions.length > 0 && (
                  <div className="chat-actions">
                    {msg.actions.map((action, aIdx) => (
                      <button
                        key={aIdx}
                        className="chat-action-chip"
                        onClick={() => onActionClick?.(action)}
                      >
                        {action.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {loading && messages.length > 0 && messages[messages.length - 1].role === 'user' && (
          <div
            className="message-row assistant loading-ghost"
            data-bubble="true"
            data-role="assistant"
            style={{ animationDelay: '0s' }}
          >
            <div className="bubble assistant">
              <div className="bubble-head">
                <span className="role-chip assistant">
                  <Bot size={12} strokeWidth={2.5} />
                  Agente
                </span>
              </div>
              <div className="skeleton-container">
                <div className="skeleton-line" />
                <div className="skeleton-line" />
                <div className="skeleton-line" />
              </div>
              <div className="message-meta">
                {generationStartTime && <GenerationTimer startTime={generationStartTime} />}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ChatWindow;
