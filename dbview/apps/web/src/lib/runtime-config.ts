/**
 * Build-time host integration knobs. Every default reproduces standalone
 * behaviour exactly — a build without these env vars is byte-equivalent to
 * upstream dbview.
 *
 * Embedded (BaselithCore plugin) builds set:
 *   VITE_API_BASE_URL=/api/dbview   (reverse-proxy prefix)
 *   VITE_BASE_PATH=/dbview/         (SPA mount path — consumed by vite.config)
 *   VITE_AUTH_MODE=gateway          (central SSO; no local login)
 */

export const API_BASE: string = import.meta.env.VITE_API_BASE_URL ?? '/api';

export const GATEWAY_AUTH: boolean = import.meta.env.VITE_AUTH_MODE === 'gateway';

/**
 * localStorage key the central auth UI (`@auth` client) writes its access
 * token under. Same-origin plugin SPAs read it for single sign-on.
 */
export const CENTRAL_TOKEN_KEY = 'auth_access_token';

export function readCentralToken(): string | null {
  if (typeof window === 'undefined') return null;
  try {
    return window.localStorage.getItem(CENTRAL_TOKEN_KEY);
  } catch {
    return null;
  }
}
