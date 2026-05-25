/**
 * Conversations API client (Fase 6).
 *
 * Sostituisce il `localStorage:llm-wiki:conversations` come source of
 * truth. Il vecchio hook `useConversations` può continuare a usare
 * cache locale per UX ottimistica, ma i dati canonici vengono dal
 * backend Postgres (RLS-isolato per tenant).
 */

import { json } from './client';

export interface ApiConversation {
  id: string;
  user_id: string;
  tenant_id: string;
  title: string;
  title_locked: boolean;
  pinned: boolean;
  created_at: string;
  updated_at: string;
  message_count?: number;
}

export interface ApiMessage {
  id: string;
  conversation_id: string;
  tenant_id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  sources?: unknown[] | null;
  metadata?: Record<string, unknown>;
  created_at: string;
}

export async function listConversations(): Promise<ApiConversation[]> {
  const r = await json<{ count: number; conversations: ApiConversation[] }>(
    '/conversations'
  );
  return r.conversations;
}

export async function createConversation(
  title = 'Nuova conversazione'
): Promise<ApiConversation> {
  return json<ApiConversation>('/conversations', {
    method: 'POST',
    body: JSON.stringify({ title }),
  });
}

export async function getConversation(id: string): Promise<ApiConversation> {
  return json<ApiConversation>(`/conversations/${encodeURIComponent(id)}`);
}

export async function updateConversation(
  id: string,
  patch: { title?: string; pinned?: boolean; title_locked?: boolean }
): Promise<ApiConversation> {
  return json<ApiConversation>(`/conversations/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: JSON.stringify(patch),
  });
}

export async function deleteConversation(id: string): Promise<void> {
  const { authFetch } = await import('./client');
  const r = await authFetch(`/conversations/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  });
  if (!r.ok && r.status !== 204) {
    throw new Error(`delete conversation failed: ${r.status}`);
  }
}

export async function listMessages(
  conversationId: string,
  opts: { limit?: number; offset?: number } = {}
): Promise<ApiMessage[]> {
  const qs = new URLSearchParams();
  if (opts.limit) qs.set('limit', String(opts.limit));
  if (opts.offset) qs.set('offset', String(opts.offset));
  const path = `/conversations/${encodeURIComponent(conversationId)}/messages${
    qs.toString() ? `?${qs}` : ''
  }`;
  const r = await json<{ count: number; messages: ApiMessage[] }>(path);
  return r.messages;
}

/**
 * Tronca: cancella `messageId` e tutti i successivi della conversation.
 * Usato da regenerate/editAndResend per allineare server↔client dopo
 * che l'utente ha rimosso turni locali.
 */
export async function truncateMessagesFrom(
  conversationId: string,
  messageId: string
): Promise<number> {
  const r = await json<{ deleted: number }>(
    `/conversations/${encodeURIComponent(conversationId)}/messages/${encodeURIComponent(
      messageId
    )}/and_after`,
    { method: 'DELETE' }
  );
  return r.deleted;
}
