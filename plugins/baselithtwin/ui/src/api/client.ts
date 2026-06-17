// Thin, typed fetch wrapper over the plugin REST API. Every call forwards the
// active UI locale via Accept-Language so backend acknowledgements come back
// localized, matching the rest of the framework's i18n contract.

import i18n from '../i18n';
import type {
  AuditEvent,
  PendingReply,
  SalientFact,
  StyleProfile,
  TwinStatus,
  WhitelistEntry,
} from './types';

const BASE = '/api/baselithtwin';

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      'Accept-Language': i18n.language || 'en',
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    const detail = await res.text().catch(() => res.statusText);
    throw new Error(`${res.status}: ${detail}`);
  }
  return (res.status === 204 ? undefined : await res.json()) as T;
}

export const api = {
  status: () => request<TwinStatus>('/status'),
  style: () => request<StyleProfile | null>('/style'),
  trainStyle: () => request<StyleProfile>('/style/train', { method: 'POST' }),

  whitelist: () => request<WhitelistEntry[]>('/whitelist'),
  addWhitelist: (contact_id: string, display_name?: string) =>
    request<{ message: string }>('/whitelist', {
      method: 'POST',
      body: JSON.stringify({ contact_id, display_name }),
    }),
  removeWhitelist: (contactId: string) =>
    request<{ message: string }>(`/whitelist/${encodeURIComponent(contactId)}`, {
      method: 'DELETE',
    }),

  facts: (contactId?: string) =>
    request<SalientFact[]>(
      `/facts${contactId ? `?contact_id=${encodeURIComponent(contactId)}` : ''}`
    ),

  replies: (onlyQueued = false) => request<PendingReply[]>(`/replies?only_queued=${onlyQueued}`),
  // The deciding identity is taken server-side from the authenticated session —
  // never sent from the client — so the audit trail can't be spoofed.
  approve: (id: string) => request<PendingReply>(`/replies/${id}/approve`, { method: 'POST' }),
  reject: (id: string) => request<PendingReply>(`/replies/${id}/reject`, { method: 'POST' }),

  audit: (limit = 50) => request<AuditEvent[]>(`/audit?limit=${limit}`),
  pause: () => request<{ paused: boolean; message: string }>('/control/pause', { method: 'POST' }),
  resume: () =>
    request<{ paused: boolean; message: string }>('/control/resume', { method: 'POST' }),
};

export const STREAM_URL = `${BASE}/stream`;
