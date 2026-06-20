// Central auth (single-source SSO) persists the access token under this key via
// the shared `@auth` AuthProvider. Reading the SAME key here makes every
// red_agent API/WS call carry the logged-in user's Bearer token, so the gateway
// RBAC gate authorises them — instead of falling back to the (often absent)
// refresh cookie and 403-ing on restricted/non-admin sessions.
const TOKEN_KEY = 'auth_access_token';
export const getToken = () => localStorage.getItem(TOKEN_KEY) ?? '';
export const setToken = (t: string) => localStorage.setItem(TOKEN_KEY, t);

export async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${getToken()}`,
      ...(init.headers ?? {}),
    },
  });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  if (res.status === 204) return undefined as T;
  const text = await res.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

export function qs(params: Record<string, string | number | undefined>): string {
  const usp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== '') usp.set(k, String(v));
  }
  const s = usp.toString();
  return s ? `?${s}` : '';
}

export function qsLoose(filters: Record<string, unknown>): string {
  const cleaned: Record<string, string | number | undefined> = {};
  for (const [k, v] of Object.entries(filters)) {
    if (v === undefined || v === null || v === '' || v === false) continue;
    cleaned[k] = typeof v === 'boolean' ? String(v) : (v as string | number);
  }
  return qs(cleaned);
}
