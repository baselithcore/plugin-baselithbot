/** Admin SSO provider management API client. */

const API_BASE = '/api/auth/sso/admin';

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

export interface SsoProvider {
  id: string;
  slug: string;
  name: string;
  protocol: 'oidc' | 'saml';
  enabled: boolean;
  auto_provision: boolean;
  config: Record<string, unknown>;
  default_roles: string[];
  has_secret: boolean;
}

export interface SsoProviderUpsert {
  name: string;
  protocol: 'oidc' | 'saml';
  enabled: boolean;
  auto_provision: boolean;
  config: Record<string, unknown>;
  secret?: string | null;
  default_roles: string[];
}

export function listProviders(token: string): Promise<SsoProvider[]> {
  return fetch(`${API_BASE}/providers`, {
    headers: authHeaders(token),
    credentials: 'include',
  }).then(handle<SsoProvider[]>);
}

export function upsertProvider(
  token: string,
  slug: string,
  body: SsoProviderUpsert
): Promise<SsoProvider> {
  return fetch(`${API_BASE}/providers/${slug}`, {
    method: 'PUT',
    headers: authHeaders(token, true),
    credentials: 'include',
    body: JSON.stringify(body),
  }).then(handle<SsoProvider>);
}

export function deleteProvider(token: string, slug: string): Promise<{ message: string }> {
  return fetch(`${API_BASE}/providers/${slug}`, {
    method: 'DELETE',
    headers: authHeaders(token),
    credentials: 'include',
  }).then(handle<{ message: string }>);
}
