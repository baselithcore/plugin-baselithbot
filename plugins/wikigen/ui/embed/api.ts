/**
 * API client per embed mini-app.
 *
 * Token recuperato da URL search param (``?token=...``) o (fallback)
 * postMessage dal parent widget loader. NON usa ``authFetch`` (no JWT,
 * no cookies) — chiamate fetch native con ``embed_token`` in body.
 *
 * Base path: ``/api/embed/*`` SAME-ORIGIN dell'iframe. Il browser non
 * invoca CORS perché iframe e API condividono l'origine
 * ``wiki.example.com``. Il widget loader inserisce un iframe puntando
 * a quell'origine, quindi le fetch interne sono same-origin.
 *
 * Per sviluppo locale (Vite proxy :5173 → :8000) il base path resta
 * ``/api/embed/*`` e Vite forwarda al backend.
 */

const BASE = '/api/embed';

export interface EmbedTheme {
  primary?: string;
  background?: string;
  text?: string;
  position?: 'bottom-right' | 'bottom-left';
  font?: string;
  height?: string;
  width?: string;
}

export interface EmbedConfig {
  embed_id: string;
  name: string;
  theme: EmbedTheme;
  welcome_message: string;
  suggested_questions: string[];
  pack: {
    label?: string;
    language?: string;
    ui?: Record<string, unknown>;
  };
  rate_limit_per_minute: number;
}

export interface EmbedSource {
  title?: string;
  folder?: string;
  slug?: string;
  page_id?: string;
  page_type?: string;
  score?: number;
}

export type EmbedStreamEvent =
  | { type: 'token'; content: string }
  | { type: 'agent'; content: string }
  | { type: 'step'; content: string }
  | { type: 'sources'; items: EmbedSource[] }
  | { type: 'hits'; count: number }
  | { type: 'done' }
  | { type: 'error'; message: string }
  | { type: string; [key: string]: unknown };

export class EmbedError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = 'EmbedError';
  }
}

export interface ChatHistoryMessage {
  role: 'user' | 'assistant';
  content: string;
}

export async function fetchEmbedConfig(token: string): Promise<EmbedConfig> {
  const res = await fetch(`${BASE}/config`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ embed_token: token }),
  });
  if (!res.ok) {
    throw new EmbedError(res.status, `config error ${res.status}`);
  }
  return (await res.json()) as EmbedConfig;
}

export async function streamEmbedChat(
  token: string,
  message: string,
  history: ChatHistoryMessage[],
  onEvent: (ev: EmbedStreamEvent) => void,
  opts: { signal?: AbortSignal; limit?: number } = {}
): Promise<void> {
  const res = await fetch(`${BASE}/chat/stream`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      embed_token: token,
      message,
      history,
      limit: opts.limit ?? 6,
    }),
    signal: opts.signal,
  });
  if (!res.ok || !res.body) {
    throw new EmbedError(res.status, `stream error ${res.status}`);
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      buffer += decoder.decode();
      break;
    }
    buffer += decoder.decode(value, { stream: true });
    let nl: number;
    while ((nl = buffer.indexOf('\n')) >= 0) {
      const line = buffer.slice(0, nl).trim();
      buffer = buffer.slice(nl + 1);
      if (!line) continue;
      try {
        onEvent(JSON.parse(line) as EmbedStreamEvent);
      } catch {
        // ignore malformed line
      }
    }
  }
  if (buffer.trim()) {
    try {
      onEvent(JSON.parse(buffer) as EmbedStreamEvent);
    } catch {
      /* noop */
    }
  }
}
