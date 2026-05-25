import type { Message, StreamEvent } from '../types';
import { ApiError, authFetch } from './client';

/**
 * Streaming chat via NDJSON. Consumer riceve ogni StreamEvent appena il backend
 * lo emette. `signal` permette di abortire lo stream (utile per stop button).
 *
 * Fase 6 multi-tenancy: passa `conversation_id` opzionale. Se omesso e
 * l'utente è autenticato, il backend auto-crea la conversation e lo
 * comunica via primo evento `{type:"conversation",id:...}`. `authFetch`
 * inietta il bearer token e gestisce auto-refresh on 401.
 */
export async function streamChat(
  message: string,
  history: Message[],
  onEvent: (ev: StreamEvent) => void,
  opts: {
    signal?: AbortSignal;
    graph?: boolean;
    limit?: number;
    conversationId?: string | null;
  } = {}
): Promise<void> {
  const body = JSON.stringify({
    message,
    history: history.map((m) => ({ role: m.role, content: m.content })),
    graph: opts.graph ?? false,
    limit: opts.limit ?? 8,
    ...(opts.conversationId ? { conversation_id: opts.conversationId } : {}),
  });

  const res = await authFetch('/chat/stream', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body,
    signal: opts.signal,
  });

  if (!res.ok || !res.body) {
    throw new ApiError(res.status, `stream error ${res.status}`);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  // NDJSON: una riga JSON per evento, separata da '\n'.
  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      buffer += decoder.decode();
      break;
    }
    buffer += decoder.decode(value, { stream: true });

    let newlineIdx: number;
    while ((newlineIdx = buffer.indexOf('\n')) >= 0) {
      const line = buffer.slice(0, newlineIdx).trim();
      buffer = buffer.slice(newlineIdx + 1);
      if (!line) continue;
      try {
        onEvent(JSON.parse(line) as StreamEvent);
      } catch (err) {
        // eslint-disable-next-line no-console
        console.warn('stream parse failed', err, line);
      }
    }
  }

  if (buffer.trim()) {
    try {
      onEvent(JSON.parse(buffer) as StreamEvent);
    } catch {
      /* noop */
    }
  }
}
