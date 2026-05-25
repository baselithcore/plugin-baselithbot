/**
 * Audit Log API Client
 */

import type { AuditLogResponse } from '../types';

const API_BASE = '/api/admin';

async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const token = localStorage.getItem('access_token');

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
    credentials: 'include',
  });

  if (response.status === 401) {
    window.location.href = '/auth/login';
    throw new Error('Session expired');
  }

  return response;
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || 'Request failed');
  }
  return response.json();
}

export async function getAuditLog(
  page = 1,
  limit = 50,
  action?: string,
  actorId?: string,
  targetId?: string
): Promise<AuditLogResponse> {
  const params = new URLSearchParams({
    page: page.toString(),
    limit: limit.toString(),
  });

  if (action) params.set('action', action);
  if (actorId) params.set('actor_id', actorId);
  if (targetId) params.set('target_id', targetId);

  const response = await fetchWithAuth(`${API_BASE}/audit-log?${params}`);
  return handleResponse<AuditLogResponse>(response);
}
