/**
 * Sessions API Client
 */

import type { SessionListResponse } from '../types';

const API_BASE = '/api/admin';

async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const token = sessionStorage.getItem('auth_access_token');

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

export async function listSessions(userId?: string): Promise<SessionListResponse> {
  const params = new URLSearchParams();
  if (userId) {
    params.set('user_id', userId);
  }

  const url = params.toString() ? `${API_BASE}/sessions?${params}` : `${API_BASE}/sessions`;

  const response = await fetchWithAuth(url);
  return handleResponse<SessionListResponse>(response);
}
