/**
 * EmbedChat — mini-app standalone caricato dentro l'iframe del widget.
 *
 * Stack minimo: niente framer-motion / react-markdown / lucide /
 * sonner / Tailwind class injection — bundle leggero. Styling inline
 * con CSS vars derivati da ``theme`` (postMessage o config endpoint).
 *
 * Comunicazione col parent loader via ``postMessage``:
 * - ``embed:ready`` quando React monta (parent può ridurre il loader skeleton).
 * - ``embed:close`` quando l'utente preme la X (parent chiude iframe).
 */

import { useEffect, useMemo, useRef, useState } from 'react';

import { fetchEmbedConfig, type EmbedConfig } from './api';
import { useEmbedChat } from './useEmbedChat';

interface EmbedChatProps {
  token: string;
}

function parentPost(message: unknown): void {
  try {
    window.parent?.postMessage(message, '*');
  } catch {
    /* sandboxed without allow-same-origin — ignore */
  }
}

function buildThemeVars(theme: EmbedConfig['theme'] | undefined): React.CSSProperties {
  const t = theme ?? {};
  return {
    ['--embed-primary' as any]: t.primary ?? '#0ea5e9',
    ['--embed-bg' as any]: t.background ?? '#ffffff',
    ['--embed-text' as any]: t.text ?? '#1f2937',
    ['--embed-font' as any]:
      t.font ?? '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  };
}

export function EmbedChat({ token }: EmbedChatProps) {
  const [config, setConfig] = useState<EmbedConfig | null>(null);
  const [configError, setConfigError] = useState<string | null>(null);
  const { messages, isStreaming, lastError, send, stop, reset } = useEmbedChat({ token });
  const scrollRef = useRef<HTMLDivElement>(null);
  const [input, setInput] = useState('');

  useEffect(() => {
    fetchEmbedConfig(token)
      .then((c) => {
        setConfig(c);
        parentPost({ type: 'embed:ready', embed_id: c.embed_id });
      })
      .catch((err) => {
        setConfigError(err?.message ?? 'errore caricamento config');
        parentPost({ type: 'embed:error', message: err?.message ?? 'config' });
      });
  }, [token]);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [messages]);

  const themeStyle = useMemo(() => buildThemeVars(config?.theme), [config?.theme]);

  if (configError) {
    return (
      <div style={{ padding: 24, fontFamily: 'sans-serif', color: '#b91c1c' }}>
        <h3 style={{ margin: '0 0 8px 0' }}>Errore</h3>
        <p style={{ margin: 0, fontSize: 14 }}>{configError}</p>
      </div>
    );
  }

  if (!config) {
    return (
      <div style={{ padding: 24, fontFamily: 'sans-serif', color: '#6b7280' }}>Caricamento…</div>
    );
  }

  const onSend = () => {
    const trimmed = input.trim();
    if (!trimmed) return;
    setInput('');
    void send(trimmed);
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        background: 'var(--embed-bg)',
        color: 'var(--embed-text)',
        fontFamily: 'var(--embed-font)',
        ...themeStyle,
      }}
    >
      <header
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '12px 16px',
          background: 'var(--embed-primary)',
          color: '#ffffff',
          fontWeight: 600,
        }}
      >
        <span>{config.name}</span>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={() => {
              reset();
            }}
            style={{
              background: 'transparent',
              border: '1px solid rgba(255,255,255,0.4)',
              color: '#ffffff',
              padding: '4px 10px',
              borderRadius: 6,
              cursor: 'pointer',
              fontSize: 12,
            }}
            title="Cancella conversazione"
            type="button"
          >
            Reset
          </button>
          <button
            onClick={() => parentPost({ type: 'embed:close' })}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#ffffff',
              fontSize: 20,
              cursor: 'pointer',
              padding: '0 4px',
              lineHeight: 1,
            }}
            title="Chiudi"
            type="button"
            aria-label="Chiudi"
          >
            ×
          </button>
        </div>
      </header>

      <div
        ref={scrollRef}
        style={{
          flex: 1,
          overflowY: 'auto',
          padding: 16,
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
        }}
      >
        {messages.length === 0 && config.welcome_message && (
          <div
            style={{
              background: '#f3f4f6',
              padding: '10px 14px',
              borderRadius: 10,
              fontSize: 14,
              lineHeight: 1.4,
              maxWidth: '85%',
            }}
          >
            {config.welcome_message}
          </div>
        )}
        {messages.length === 0 && config.suggested_questions.length > 0 && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8 }}>
            {config.suggested_questions.map((q, i) => (
              <button
                key={i}
                onClick={() => void send(q)}
                disabled={isStreaming}
                type="button"
                style={{
                  textAlign: 'left',
                  background: '#ffffff',
                  border: '1px solid #e5e7eb',
                  borderRadius: 8,
                  padding: '8px 12px',
                  fontSize: 13,
                  cursor: 'pointer',
                  color: 'var(--embed-text)',
                }}
              >
                {q}
              </button>
            ))}
          </div>
        )}
        {messages.map((m) => (
          <div
            key={m.id}
            style={{
              alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
              maxWidth: '85%',
              background: m.role === 'user' ? 'var(--embed-primary)' : '#f3f4f6',
              color: m.role === 'user' ? '#ffffff' : 'var(--embed-text)',
              padding: '10px 14px',
              borderRadius: 12,
              fontSize: 14,
              lineHeight: 1.45,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word',
            }}
          >
            {m.content || (m.streaming ? '…' : '')}
            {m.error && (
              <div style={{ color: '#b91c1c', fontSize: 12, marginTop: 6 }}>{m.error}</div>
            )}
          </div>
        ))}
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          onSend();
        }}
        style={{
          display: 'flex',
          gap: 8,
          padding: 12,
          borderTop: '1px solid #e5e7eb',
          background: '#ffffff',
        }}
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Scrivi un messaggio…"
          disabled={isStreaming}
          style={{
            flex: 1,
            padding: '10px 12px',
            border: '1px solid #d1d5db',
            borderRadius: 8,
            fontSize: 14,
            outline: 'none',
            fontFamily: 'inherit',
            color: 'var(--embed-text)',
          }}
        />
        {isStreaming ? (
          <button
            type="button"
            onClick={stop}
            style={{
              padding: '10px 16px',
              border: 'none',
              borderRadius: 8,
              background: '#ef4444',
              color: '#ffffff',
              fontSize: 14,
              cursor: 'pointer',
            }}
          >
            Stop
          </button>
        ) : (
          <button
            type="submit"
            disabled={!input.trim()}
            style={{
              padding: '10px 16px',
              border: 'none',
              borderRadius: 8,
              background: 'var(--embed-primary)',
              color: '#ffffff',
              fontSize: 14,
              cursor: input.trim() ? 'pointer' : 'not-allowed',
              opacity: input.trim() ? 1 : 0.5,
            }}
          >
            Invia
          </button>
        )}
      </form>
      {lastError && !isStreaming && (
        <div
          style={{
            background: '#fee2e2',
            color: '#991b1b',
            padding: '6px 12px',
            fontSize: 12,
            textAlign: 'center',
          }}
        >
          {lastError}
        </div>
      )}
    </div>
  );
}
