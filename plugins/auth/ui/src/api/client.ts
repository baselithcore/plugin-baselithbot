/**
 * Shared fetch helpers (bearer auth + JSON error handling).
 */

export async function fetchWithAuth(url: string, options: RequestInit = {}): Promise<Response> {
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
