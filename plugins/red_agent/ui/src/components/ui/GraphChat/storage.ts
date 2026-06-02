import type { ChatMessage } from './types';

const STORAGE_KEY = (target: string) => `red_agent.graph_chat.${target}`;
const MAX_PERSIST_TURNS = 30;

export function loadMessages(target: string): ChatMessage[] {
  if (!target) return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY(target));
    if (!raw) return [];
    const parsed = JSON.parse(raw) as ChatMessage[];
    return parsed.filter((m) => !m.pending);
  } catch {
    return [];
  }
}

export function persistMessages(target: string, messages: ChatMessage[]): void {
  if (!target) return;
  try {
    const trimmed = messages
      .filter((m) => !m.pending)
      .slice(-MAX_PERSIST_TURNS)
      .map((m) => ({ ...m, error: m.error ?? null }));
    localStorage.setItem(STORAGE_KEY(target), JSON.stringify(trimmed));
  } catch {
    /* noop */
  }
}
