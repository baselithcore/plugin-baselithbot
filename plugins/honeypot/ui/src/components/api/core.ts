/**
 * Core API Utilities
 * Base fetch wrapper with automatic token refresh and utilities
 */

import { getAuthHeaders, refreshAccessToken } from './auth';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

/**
 * Core API fetch with automatic token refresh on 401/403.
 * @param path - API path (e.g., '/events')
 * @param init - Fetch options
 * @param _retried - Internal flag to prevent infinite retry loops
 */
export async function honeypotApiFetch<T>(
  path: string,
  init?: RequestInit,
  _retried = false
): Promise<T> {
  const response = await fetch(`${API_BASE}/honeypot${path}`, {
    credentials: 'include', // Include cookies for refresh token fallback
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
      ...(init?.headers || {}),
    },
    ...init,
  });

  if (!response.ok) {
    // Token expired - try to refresh and retry once
    if ((response.status === 401 || response.status === 403) && !_retried) {
      const refreshed = await refreshAccessToken();
      if (refreshed) {
        // Retry the original request with new token
        return honeypotApiFetch<T>(path, init, true);
      }
      // Refresh failed - dispatch unauthorized event
      window.dispatchEvent(new CustomEvent('auth:unauthorized'));
    }

    const detail = await response.text();
    throw new Error(detail || 'Honeypot API request failed');
  }

  // Handle 204 No Content and other empty responses
  if (response.status === 204 || response.headers.get('content-length') === '0') {
    return undefined as T;
  }

  return (await response.json()) as T;
}

/**
 * Normalize IP address for display
 * Converts IPv6 loopback (::1) and IPv4 loopback (127.0.0.1) to "localhost"
 */
export function normalizeIpDisplay(ip: string): string {
  if (!ip || ip === 'unknown') return 'Unknown';

  // Check for localhost variants
  if (ip === '::1' || ip === '127.0.0.1' || ip.toLowerCase() === 'localhost') {
    return 'localhost';
  }

  // Check for IPv4-mapped IPv6 localhost (::ffff:127.0.0.1)
  if (ip.startsWith('::ffff:127.')) {
    return 'localhost';
  }

  return ip;
}
