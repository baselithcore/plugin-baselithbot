/**
 * Authentication & Token Management
 * Handles token refresh logic and auth state
 */

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

// Token refresh state - prevents multiple simultaneous refresh attempts
let isRefreshing = false;
let refreshPromise: Promise<boolean> | null = null;

/**
 * Get auth headers dynamically (token may change during session)
 */
export function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};

  // Bearer token from auth system (primary)
  const token = sessionStorage.getItem('auth_access_token');
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Legacy API key support (secondary)
  const API_KEY = import.meta.env.VITE_API_KEY || '';
  if (API_KEY) {
    headers['X-API-Key'] = API_KEY;
  }

  return headers;
}

/**
 * Attempt to refresh the access token using the refresh token cookie.
 * Returns true if refresh succeeded, false otherwise.
 */
export async function refreshAccessToken(): Promise<boolean> {
  // If already refreshing, wait for the existing refresh to complete
  if (isRefreshing && refreshPromise) {
    return refreshPromise;
  }

  isRefreshing = true;
  refreshPromise = (async () => {
    try {
      const resp = await fetch(`${API_BASE}/auth/refresh`, {
        method: 'POST',
        credentials: 'include', // Include refresh token cookie
        headers: { 'Content-Type': 'application/json' },
      });

      if (resp.ok) {
        const data = await resp.json();
        if (data.access_token) {
          sessionStorage.setItem('auth_access_token', data.access_token);
          console.debug('[API] Token refreshed successfully');
          return true;
        }
      }
      console.warn('[API] Token refresh failed:', resp.status);
      return false;
    } catch (e) {
      console.error('[API] Token refresh error:', e);
      return false;
    } finally {
      isRefreshing = false;
      refreshPromise = null;
    }
  })();

  return refreshPromise;
}
