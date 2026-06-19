/**
 * Shared fetch helpers (bearer auth + JSON error handling).
 */

// Single source of truth for the access token. MUST match the key/storage the
// auth context writes on login (useAuthContext: localStorage 'auth_access_token').
// localStorage is shared across all same-origin tabs so a plugin opened in a new
// tab inherits the session. Splitting these silently sends a stale token →
// spurious 401/403 (e.g. admin routes failing right after a role change).
export function getAccessToken(): string | null {
  return localStorage.getItem('auth_access_token');
}

export async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
  const token = getAccessToken();
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

export async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }));
    throw new Error(error.detail || 'Request failed');
  }
  if (response.status === 204) {
    return undefined as unknown as T;
  }
  return response.json();
}
