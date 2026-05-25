/**
 * Auth API client (Fase 6).
 *
 * Tutte le chiamate vanno a `/auth/*` (NON `/api/auth`). Cookie refresh
 * httpOnly è gestito dal browser; access token torna nel JSON body.
 *
 * Best practice 2026:
 * - Access token → setAccessToken (in-memory, no localStorage).
 * - `credentials: 'include'` su login/refresh/logout per il cookie.
 * - Errors mappati su `ApiError` con status code visible UI-side.
 */

import { ApiError, BASE, authFetch, setAccessToken } from './client';

const AUTH_BASE = BASE.replace(/\/api$/, '') + '/auth';

export interface GroupRef {
  id: string;
  slug: string;
  name: string;
  is_system?: boolean;
}

export interface AuthUser {
  id: string;
  email: string;
  display_name: string;
  tenant_id: string;
  role: 'admin' | 'user';
  is_active: boolean;
  created_at?: string | null;
  last_login_at?: string | null;
  // RBAC (Fase 7). Backend popola da DB (user_roles → role_permissions).
  // Liste vuote in dev/setup mode → trattare come "nessun grant esplicito".
  roles?: string[];
  permissions?: string[];
  domains?: string[];
  // Group membership (mig 015). I gruppi sono read-only lato FE — il
  // gating effettivo passa sempre da `permissions` (già aggregati dal
  // backend via user_roles ∪ group_roles).
  groups?: GroupRef[];
  // Force password change baseline (009). True ⇒ frontend deve
  // forzare /auth/password prima di consentire qualsiasi altra azione.
  must_change_password?: boolean;
}

export interface InvitePeek {
  valid: boolean;
  email?: string;
  role_slug?: string | null;
  display_name?: string;
  expires_at?: string;
  reason?: 'expired' | 'used' | 'unknown';
}

export interface InviteAcceptArgs {
  token: string;
  password: string;
  display_name?: string;
}

export async function peekInvite(
  token: string,
  signal?: AbortSignal
): Promise<InvitePeek> {
  const res = await fetch(
    `${AUTH_BASE}/invite/${encodeURIComponent(token)}`,
    { credentials: 'include', signal }
  );
  if (!res.ok) {
    return { valid: false, reason: 'unknown' };
  }
  return (await res.json()) as InvitePeek;
}

export async function acceptInvite(
  args: InviteAcceptArgs,
  signal?: AbortSignal
): Promise<TokenResponse> {
  const r = await postJson<TokenResponse>('/invite/accept', args, signal);
  setAccessToken(r.access_token);
  return r;
}

export interface InviteCreateArgs {
  email: string;
  role_slug?: string | null;
  tenant_slug?: string | null;
  display_name?: string;
  note?: string;
  ttl_hours?: number;
}

export interface InviteCreated {
  id: string;
  email: string;
  accept_url: string;
  expires_at: string;
}

export async function createInvite(
  args: InviteCreateArgs,
  signal?: AbortSignal
): Promise<InviteCreated> {
  return postJsonAuth<InviteCreated>('/invite', args, signal);
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_at: string;
  user_id: string;
  tenant_id: string;
  role: 'admin' | 'user';
  email: string;
}

async function postJson<T>(
  path: string,
  body?: unknown,
  signal?: AbortSignal
): Promise<T> {
  const res = await fetch(`${AUTH_BASE}${path}`, {
    method: 'POST',
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
    credentials: 'include',
    signal,
  });
  if (!res.ok) {
    const txt = await res.text().catch(() => res.statusText);
    throw new ApiError(res.status, txt);
  }
  return (await res.json()) as T;
}

/**
 * Variante autenticata: attacca ``Authorization: Bearer <access_token>``
 * via :func:`authFetch` (retry-on-401 con refresh built-in). Usata da
 * endpoint che richiedono ``require_user`` / ``require_admin`` /
 * ``require_permission`` lato server (es. POST ``/auth/invite``,
 * POST ``/auth/password``). ``postJson`` bare resta per i flussi
 * pre-auth (login/register/refresh/logout/bootstrap) e quelli che
 * settano l'access token loro stessi (accept-invite).
 */
async function postJsonAuth<T>(
  path: string,
  body?: unknown,
  signal?: AbortSignal
): Promise<T> {
  const res = await authFetch(`${AUTH_BASE}${path}`, {
    method: 'POST',
    absolute: true,
    body: body ? JSON.stringify(body) : undefined,
    signal,
  });
  if (!res.ok) {
    const txt = await res.text().catch(() => res.statusText);
    throw new ApiError(res.status, txt);
  }
  return (await res.json()) as T;
}

export async function login(
  email: string,
  password: string,
  signal?: AbortSignal
): Promise<TokenResponse> {
  const r = await postJson<TokenResponse>('/login', { email, password }, signal);
  setAccessToken(r.access_token);
  return r;
}

export interface BootstrapStatus {
  needs_bootstrap: boolean;
  users_count: number;
}

export interface BootstrapArgs {
  email: string;
  password: string;
  display_name?: string;
  tenant_slug?: string;
}

export async function bootstrapStatus(
  signal?: AbortSignal
): Promise<BootstrapStatus> {
  const res = await fetch(`${AUTH_BASE}/bootstrap/status`, {
    method: 'GET',
    credentials: 'include',
    signal,
  });
  if (!res.ok) {
    throw new ApiError(res.status, await res.text().catch(() => res.statusText));
  }
  return (await res.json()) as BootstrapStatus;
}

export async function bootstrap(
  args: BootstrapArgs,
  signal?: AbortSignal
): Promise<TokenResponse> {
  const r = await postJson<TokenResponse>('/bootstrap', args, signal);
  setAccessToken(r.access_token);
  return r;
}

export interface RegisterArgs {
  email: string;
  password: string;
  display_name?: string;
  tenant_name?: string;
}

export async function register(
  args: RegisterArgs,
  signal?: AbortSignal
): Promise<TokenResponse> {
  const r = await postJson<TokenResponse>('/register', args, signal);
  setAccessToken(r.access_token);
  return r;
}

export async function logout(signal?: AbortSignal): Promise<void> {
  try {
    await postJson<{ status: string }>('/logout', undefined, signal);
  } finally {
    // Locale: drop access in ogni caso. Cookie pulito server-side.
    setAccessToken(null);
  }
}

export async function logoutAll(signal?: AbortSignal): Promise<number> {
  try {
    const r = await postJson<{ revoked_count: number }>(
      '/logout-all',
      undefined,
      signal
    );
    return r.revoked_count;
  } finally {
    setAccessToken(null);
  }
}

/**
 * Refresh proattivo (raro: lo fa già il client wrapper su 401). Esposto
 * per il bootstrap App.tsx — al primo mount tentiamo refresh per ripristinare
 * sessione persistita via cookie, evitando di mostrare login se già loggato.
 */
export async function refresh(signal?: AbortSignal): Promise<TokenResponse | null> {
  try {
    const r = await postJson<TokenResponse>('/refresh', undefined, signal);
    return r;
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) return null;
    throw err;
  }
}

export async function me(signal?: AbortSignal): Promise<AuthUser> {
  // Auth endpoints stanno fuori dal prefix `/api` (router montato con
  // prefix `/auth`). Usiamo authFetch con absolute=true per saltare
  // il prepend BASE — manteniamo comunque auto-refresh on 401.
  const { authFetch } = await import('./client');
  const url = `${AUTH_BASE}/me`;
  const r = await authFetch(url, { signal, absolute: true });
  if (!r.ok) {
    const txt = await r.text().catch(() => r.statusText);
    throw new ApiError(r.status, txt);
  }
  return (await r.json()) as AuthUser;
}

export interface PasswordChangeArgs {
  current_password: string;
  new_password: string;
}

export async function changePassword(
  args: PasswordChangeArgs,
  signal?: AbortSignal
): Promise<void> {
  // Endpoint richiede require_user → Bearer obbligatorio.
  await postJsonAuth<{ status: string }>('/password', args, signal);
  // Server revoca tutti i refresh → access in-memory non più valido.
  setAccessToken(null);
}
