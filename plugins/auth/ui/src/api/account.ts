/** Self-service "My Account" API client. */

const API_BASE = '/api/auth/me';

function authHeaders(token: string, json = false): HeadersInit {
  return {
    Authorization: `Bearer ${token}`,
    ...(json ? { 'Content-Type': 'application/json' } : {}),
  };
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(err.detail || 'Request failed');
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

export interface Account {
  id: string;
  email: string;
  username: string | null;
  full_name: string | null;
  roles: string[];
  mfa_enabled: boolean;
  email_verified: boolean;
  status: string;
  passkey_count: number;
  last_login: string | null;
  last_login_ip: string | null;
}

export interface SessionInfo {
  id: string;
  created_at: string | null;
  expires_at: string | null;
  current: boolean;
}

export interface ActivityEntry {
  event: string;
  method: string;
  success: boolean;
  ip_address: string | null;
  user_agent: string | null;
  risk_score: number;
  created_at: string | null;
}

export function getAccount(token: string): Promise<Account> {
  return fetch(`${API_BASE}/account`, { headers: authHeaders(token), credentials: 'include' }).then(
    handle<Account>
  );
}

export function updateProfile(token: string, fullName: string, username: string): Promise<Account> {
  return fetch(`${API_BASE}/profile`, {
    method: 'PATCH',
    headers: authHeaders(token, true),
    credentials: 'include',
    body: JSON.stringify({ full_name: fullName || null, username: username || null }),
  }).then(handle<Account>);
}

export function changePassword(
  token: string,
  current: string,
  next: string
): Promise<{ message: string }> {
  return fetch(`${API_BASE}/change-password`, {
    method: 'POST',
    headers: authHeaders(token, true),
    credentials: 'include',
    body: JSON.stringify({ current_password: current, new_password: next }),
  }).then(handle<{ message: string }>);
}

export function disableMfaSelf(token: string, code: string): Promise<{ message: string }> {
  return fetch(`${API_BASE}/mfa/disable`, {
    method: 'POST',
    headers: authHeaders(token, true),
    credentials: 'include',
    body: JSON.stringify({ code }),
  }).then(handle<{ message: string }>);
}

export function listSessions(token: string): Promise<SessionInfo[]> {
  return fetch(`${API_BASE}/sessions`, {
    headers: authHeaders(token),
    credentials: 'include',
  }).then(handle<SessionInfo[]>);
}

export function revokeSession(token: string, id: string): Promise<{ message: string }> {
  return fetch(`${API_BASE}/sessions/${id}`, {
    method: 'DELETE',
    headers: authHeaders(token),
    credentials: 'include',
  }).then(handle<{ message: string }>);
}

export function revokeOtherSessions(token: string): Promise<{ message: string }> {
  return fetch(`${API_BASE}/sessions/revoke-others`, {
    method: 'POST',
    headers: authHeaders(token),
    credentials: 'include',
  }).then(handle<{ message: string }>);
}

export function getActivity(token: string): Promise<ActivityEntry[]> {
  return fetch(`${API_BASE}/activity`, {
    headers: authHeaders(token),
    credentials: 'include',
  }).then(handle<ActivityEntry[]>);
}

export interface ApiKeyInfo {
  id: string;
  name: string;
  prefix: string;
  scopes: string[];
  expires_at: string | null;
  last_used_at: string | null;
  revoked_at: string | null;
  created_at: string | null;
}

export interface ApiKeyCreated {
  key: string;
  info: ApiKeyInfo;
}

export function listApiKeys(token: string): Promise<ApiKeyInfo[]> {
  return fetch(`${API_BASE}/api-keys`, {
    headers: authHeaders(token),
    credentials: 'include',
  }).then(handle<ApiKeyInfo[]>);
}

export function createApiKey(
  token: string,
  name: string,
  expiresInDays: number | null
): Promise<ApiKeyCreated> {
  return fetch(`${API_BASE}/api-keys`, {
    method: 'POST',
    headers: authHeaders(token, true),
    credentials: 'include',
    body: JSON.stringify({ name, expires_in_days: expiresInDays }),
  }).then(handle<ApiKeyCreated>);
}

export function revokeApiKey(token: string, id: string): Promise<{ message: string }> {
  return fetch(`${API_BASE}/api-keys/${id}`, {
    method: 'DELETE',
    headers: authHeaders(token),
    credentials: 'include',
  }).then(handle<{ message: string }>);
}
