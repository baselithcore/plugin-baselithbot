/**
 * Memorie utente API client (Fase 6).
 *
 * RAG personale: testi/preferenze persistite per-tenant via pgvector.
 * Embed sincrono server-side (BGE-M3); il client invia solo testo.
 */

import { authFetch, json } from './client';

export type MemoryKind = 'note' | 'fact' | 'preference';

export interface ApiMemory {
  id: string;
  tenant_id: string;
  user_id: string;
  kind: MemoryKind;
  key: string | null;
  value: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  /** valorizzato solo per /search */
  similarity?: number;
}

export async function listMemories(kind?: MemoryKind): Promise<ApiMemory[]> {
  const qs = kind ? `?kind=${encodeURIComponent(kind)}` : '';
  const r = await json<{ count: number; memories: ApiMemory[] }>(`/memories${qs}`);
  return r.memories;
}

export interface MemoryCreateArgs {
  value: string;
  kind?: MemoryKind;
  key?: string | null;
  metadata?: Record<string, unknown> | null;
}

export async function createMemory(args: MemoryCreateArgs): Promise<ApiMemory> {
  return json<ApiMemory>('/memories', {
    method: 'POST',
    body: JSON.stringify(args),
  });
}

export async function upsertPreference(
  key: string,
  value: string,
  metadata?: Record<string, unknown>
): Promise<ApiMemory> {
  return json<ApiMemory>('/memories/preferences', {
    method: 'PUT',
    body: JSON.stringify({ key, value, metadata }),
  });
}

export async function deleteMemory(id: string): Promise<void> {
  const r = await authFetch(`/memories/${encodeURIComponent(id)}`, {
    method: 'DELETE',
  });
  if (!r.ok && r.status !== 204) {
    throw new Error(`delete memory failed: ${r.status}`);
  }
}

export interface SearchArgs {
  query: string;
  top_k?: number;
  kind?: MemoryKind;
  min_similarity?: number;
  only_mine?: boolean;
}

export async function searchMemories(args: SearchArgs): Promise<ApiMemory[]> {
  const r = await json<{ count: number; results: ApiMemory[] }>('/memories/search', {
    method: 'POST',
    body: JSON.stringify(args),
  });
  return r.results;
}
