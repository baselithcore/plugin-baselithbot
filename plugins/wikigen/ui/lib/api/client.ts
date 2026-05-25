/**
 * Fetch wrapper centrale (Fase 6).
 *
 * Responsabilità:
 * - Inietta `Authorization: Bearer <access>` quando presente.
 * - Gestisce 401 → tenta auto-refresh via `/auth/refresh` (cookie httpOnly)
 *   → se refresh OK retry one-shot; altrimenti emette evento `auth:logout`
 *   che `AuthContext` ascolta per mostrare la login page.
 * - `credentials: 'include'` su tutte le request (refresh cookie).
 *
 * Access token NON va in localStorage (vulnerabile XSS): vive solo in
 * memoria via questo modulo. AuthContext lo setta dopo login/refresh.
 */

export const BASE = import.meta.env.VITE_API_URL ?? '/api';

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

// --- access token in-memory ----------------------------------------------

let accessToken: string | null = null;
let refreshPromise: Promise<boolean> | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

// --- auth events bus -----------------------------------------------------
//
// Disaccoppia il client dal React tree. AuthContext ascolta `auth:logout`
// per mostrare la login page; `auth:refreshed` per aggiornare il token
// in state.

type AuthEvent = 'auth:logout' | 'auth:refreshed';
const listeners = new Map<AuthEvent, Set<(payload?: unknown) => void>>();

export function onAuthEvent(
  event: AuthEvent,
  listener: (payload?: unknown) => void
): () => void {
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

// --- refresh handling ----------------------------------------------------

/**
 * Race-safe refresh: se più request 401-ano contemporaneamente, una sola
 * chiamata `/auth/refresh` viene effettuata e tutte aspettano il risultato.
 */
async function tryRefresh(): Promise<boolean> {
  if (refreshPromise) return refreshPromise;
  refreshPromise = (async () => {
    try {
      const r = await fetch(`${BASE.replace(/\/api$/, '')}/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
      });
      if (!r.ok) return false;
      const data = (await r.json()) as { access_token?: string };
      if (!data.access_token) return false;
      setAccessToken(data.access_token);
      emitAuthEvent('auth:refreshed', data);
      return true;
    } catch {
      return false;
    } finally {
      refreshPromise = null;
    }
  })();
  return refreshPromise;
}

// --- core fetch ----------------------------------------------------------

function buildHeaders(init?: RequestInit): Headers {
  const headers = new Headers(init?.headers);
  if (!headers.has('Content-Type') && init?.body && !(init.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }
  if (accessToken) {
    headers.set('Authorization', `Bearer ${accessToken}`);
  }
  return headers;
}

/**
 * Fetch + auto-refresh su 401. Restituisce `Response` raw per lasciare
 * al chiamante la libertà di gestire body/stream.
 */
export async function authFetch(
  path: string,
  init?: RequestInit & { absolute?: boolean }
): Promise<Response> {
  const url = init?.absolute ? path : `${BASE}${path}`;
  const doFetch = () =>
    fetch(url, {
      ...init,
      credentials: 'include',
      headers: buildHeaders(init),
    });

  let res = await doFetch();
  if (res.status !== 401) return res;

  const refreshed = await tryRefresh();
  if (!refreshed) {
    setAccessToken(null);
    emitAuthEvent('auth:logout');
    return res;
  }
  res = await doFetch();
  return res;
}

/**
 * JSON helper con auth + auto-refresh built-in.
 *
 * Compat: signature legacy preservata. I 18 call site esistenti continuano
 * a funzionare; ricevono in più il comportamento auth-aware.
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
