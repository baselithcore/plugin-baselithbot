/**
 * Central fetch wrapper.
 *
 * Identity is owned by the ecosystem ``auth`` plugin. The shared ``@auth``
 * context stores the access token in ``localStorage['auth_access_token']``
 * (same-origin, shared across the dashboard + every plugin tab) and refreshes
 * it proactively. This client simply reads that token fresh on every request
 * and injects ``Authorization: Bearer <token>`` — no own token store, no own
 * refresh. On a 401 it emits ``auth:logout`` so the app can hand control back
 * to the central login wall.
 */

export const BASE = import.meta.env.VITE_API_URL ?? '/api';

/** localStorage key written by the shared ``@auth`` provider. */
const TOKEN_KEY = 'auth_access_token';

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export class AuthRequiredError extends ApiError {
  constructor(message = 'Autenticazione richiesta') {
    super(401, message);
    this.name = 'AuthRequiredError';
  }
}

// --- access token (read-only mirror of the central @auth store) ----------

export function getAccessToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

/**
 * Legacy no-op kept for source compatibility: the wiki no longer owns the
 * access token — the central ``@auth`` provider is the single writer.
 */
export function setAccessToken(_token: string | null): void {
  /* central auth owns the token store */
}

// --- auth events bus -----------------------------------------------------

type AuthEvent = 'auth:logout' | 'auth:refreshed';
const listeners = new Map<AuthEvent, Set<(payload?: unknown) => void>>();

export function onAuthEvent(event: AuthEvent, listener: (payload?: unknown) => void): () => void {
  if (!listeners.has(event)) listeners.set(event, new Set());
  listeners.get(event)!.add(listener);
  return () => listeners.get(event)?.delete(listener);
}

function emitAuthEvent(event: AuthEvent, payload?: unknown): void {
  listeners.get(event)?.forEach((l) => {
    try {
      l(payload);
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn(`[auth-event:${event}] listener error`, err);
    }
  });
}

// --- core fetch ----------------------------------------------------------

function buildHeaders(init?: RequestInit): Headers {
  const headers = new Headers(init?.headers);
  if (!headers.has('Content-Type') && init?.body && !(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }
  const token = getAccessToken();
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  return headers;
}

/**
 * Fetch with the central bearer token attached. Returns the raw ``Response``
 * so callers keep control over body/stream. A 401 emits ``auth:logout`` (the
 * central session has lapsed) and is surfaced to the caller unchanged.
 */
export async function authFetch(
  path: string,
  init?: RequestInit & { absolute?: boolean }
): Promise<Response> {
  const url = init?.absolute ? path : `${BASE}${path}`;
  const res = await fetch(url, {
    ...init,
    credentials: 'include',
    headers: buildHeaders(init),
  });
  if (res.status === 401) {
    emitAuthEvent('auth:logout');
  }
  return res;
}

/**
 * JSON helper with auth built-in. Signature preserved so existing call sites
 * keep working.
 */
export async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await authFetch(path, init);
  if (!res.ok) {
    if (res.status === 401) {
      throw new AuthRequiredError(await res.text().catch(() => 'unauthorized'));
    }
    throw new ApiError(res.status, await res.text().catch(() => res.statusText));
  }
  return (await res.json()) as T;
}
