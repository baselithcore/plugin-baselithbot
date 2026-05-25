import type { UserPublic, LoginResponse, MeResponse } from '@dbview/shared';
import { API_BASE_URL } from './api.js';

let accessToken: string | null = null;
let currentUser: UserPublic | null = null;

const listeners = new Set<() => void>();

export function getAccessToken(): string | null {
  return accessToken;
}

export function getCurrentUser(): UserPublic | null {
  return currentUser;
}

export function setSession(token: string | null, user: UserPublic | null): void {
  accessToken = token;
  currentUser = user;
  for (const l of listeners) l();
}

export function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

let inflightRefresh: Promise<LoginResponse | null> | null = null;

export async function refreshSession(): Promise<LoginResponse | null> {
  if (inflightRefresh) return inflightRefresh;
  inflightRefresh = (async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
      });
      if (!res.ok) return null;
      const data = (await res.json()) as LoginResponse;
      setSession(data.accessToken, data.user);
      return data;
    } catch {
      return null;
    } finally {
      inflightRefresh = null;
    }
  })();
  return inflightRefresh;
}

export async function bootstrapSession(): Promise<UserPublic | null> {
  // Attempt refresh on app load. If cookie still valid → access token in memory.
  const refreshed = await refreshSession();
  if (!refreshed) return null;
  return refreshed.user;
}

export async function meRequest(): Promise<UserPublic | null> {
  const token = getAccessToken();
  if (!token) return null;
  try {
    const res = await fetch(`${API_BASE_URL}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
      credentials: 'include',
    });
    if (!res.ok) return null;
    const data = (await res.json()) as MeResponse;
    return data.user;
  } catch {
    return null;
  }
}

export async function logoutRequest(): Promise<void> {
  try {
    await fetch(`${API_BASE_URL}/auth/logout`, {
      method: 'POST',
      credentials: 'include',
    });
  } finally {
    setSession(null, null);
  }
}
