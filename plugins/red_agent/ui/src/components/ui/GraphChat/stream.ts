import { getToken } from '../../../lib/api';

export function uid(): string {
  return Math.random().toString(36).slice(2, 10);
}

export async function* streamChat(
  body: object,
  signal: AbortSignal
): AsyncGenerator<
  | { type: 'start'; promptChars: number }
  | { type: 'delta'; text: string }
  | { type: 'error'; message: string }
  | { type: 'end' }
> {
  const res = await fetch('/red-agent/graph/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'text/event-stream',
      Authorization: `Bearer ${getToken()}`,
    },
    body: JSON.stringify(body),
    signal,
  });
  if (!res.ok) {
    yield { type: 'error', message: `${res.status} ${await res.text()}` };
    return;
  }
  if (!res.body) {
    yield { type: 'error', message: 'No response body' };
    return;
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let sepIdx: number;
    while ((sepIdx = buffer.indexOf('\n\n')) !== -1) {
      const block = buffer.slice(0, sepIdx);
      buffer = buffer.slice(sepIdx + 2);
      const evt = parseSseBlock(block);
      if (!evt) continue;
      if (evt.event === 'start') {
        yield { type: 'start', promptChars: Number(evt.data?.prompt_chars ?? 0) };
      } else if (evt.event === 'delta' && typeof evt.data?.text === 'string') {
        yield { type: 'delta', text: evt.data.text };
      } else if (evt.event === 'end') {
        yield { type: 'end' };
      } else if (evt.event === 'error') {
        yield { type: 'error', message: String(evt.data?.message ?? 'unknown error') };
      }
    }
  }
}

function parseSseBlock(block: string): { event: string; data: Record<string, unknown> } | null {
  let event = 'message';
  const dataLines: string[] = [];
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim();
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).trim());
  }
  if (dataLines.length === 0) return null;
  const raw = dataLines.join('\n');
  try {
    return { event, data: JSON.parse(raw) as Record<string, unknown> };
  } catch {
    return { event, data: { text: raw } };
  }
}
