import type { UserPublic, LoginResponse, MeResponse } from '@dbview/shared';
import { API_BASE, CENTRAL_TOKEN_KEY, GATEWAY_AUTH, readCentralToken } from './runtime-config.js';

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

/**
 * Gateway (central SSO) session: the access token is minted by the host's
 * auth console and shared via localStorage; dbview just validates it against
 * /auth/me (the reverse proxy resolves it to a forwarded identity).
 */
async function gatewaySession(): Promise<LoginResponse | null> {
  const token = readCentralToken();
  if (!token) {
    setSession(null, null);
    return null;
  }
  try {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` },
      credentials: 'include',
    });
    if (!res.ok) {
      setSession(null, null);
      return null;
    }
    const data = (await res.json()) as MeResponse;
    setSession(token, data.user);
    return { accessToken: token, expiresIn: 0, user: data.user };
  } catch {
    setSession(null, null);
    return null;
  }
}

export async function refreshSession(): Promise<LoginResponse | null> {
  if (inflightRefresh) return inflightRefresh;
  inflightRefresh = (async () => {
    try {
      if (GATEWAY_AUTH) return await gatewaySession();
      const res = await fetch(`${API_BASE}/auth/refresh`, {
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

// Cross-tab / host-console SSO sync: when the central token appears, changes
// or is cleared in another same-origin tab, re-resolve the session in place.
if (GATEWAY_AUTH && typeof window !== 'undefined') {
  window.addEventListener('storage', (event) => {
    if (event.key === null || event.key === CENTRAL_TOKEN_KEY) {
      void refreshSession();
    }
  });
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
    const res = await fetch(`${API_BASE}/auth/me`, {
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
  if (GATEWAY_AUTH) {
    // The session belongs to the central identity provider; drop the local
    // snapshot and hand control back to the host console (which owns logout).
    setSession(null, null);
    window.location.assign('/');
    return;
  }
  try {
    await fetch(`${API_BASE}/auth/logout`, {
      method: 'POST',
      credentials: 'include',
    });
  } finally {
    setSession(null, null);
  }
}
