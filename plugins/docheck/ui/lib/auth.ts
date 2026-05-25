'use client';

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? 'http://127.0.0.1:8765/api/v1';
const TOKEN_KEY = 'docheck.token';

export interface AuthSession {
  user_id: string;
  email: string;
  roles: string[];
  token: string;
}

export async function login(email: string, password: string): Promise<AuthSession> {
  const res = await fetch(`${BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error(`Login failed: ${res.status}`);
  const session: AuthSession = await res.json();
  localStorage.setItem(TOKEN_KEY, session.token);
  localStorage.setItem(`${TOKEN_KEY}.session`, JSON.stringify(session));
  return session;
}

export function logout(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(`${TOKEN_KEY}.session`);
}

export function getToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getSession(): AuthSession | null {
  if (typeof window === 'undefined') return null;
  const raw = localStorage.getItem(`${TOKEN_KEY}.session`);
  return raw ? (JSON.parse(raw) as AuthSession) : null;
}

const TENANT_KEY = 'docheck.tenant';

export function getTenant(): string {
  if (typeof window === 'undefined') return 'default';
  return localStorage.getItem(TENANT_KEY) ?? 'default';
}

export function setTenant(tenant: string): void {
  localStorage.setItem(TENANT_KEY, tenant);
}

export function authHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  const tok = getToken();
  if (tok) headers.Authorization = `Bearer ${tok}`;
  if (typeof window !== 'undefined') {
    headers['X-Tenant-Id'] = getTenant();
  }
  return headers;
}

let _intercepted = false;

export function installAuthInterceptor(): void {
  if (typeof window === 'undefined' || _intercepted) return;
  _intercepted = true;
  const origFetch = window.fetch.bind(window);

  window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
    const res = await origFetch(input as RequestInfo, init);
    if (res.status !== 401) return res;

    const url = typeof input === 'string' ? input : input instanceof URL ? input.href : input.url;
    if (!url.startsWith(BASE)) return res;

    // Login endpoint 401 = bad credentials, do not auto-logout
    if (url.includes('/auth/login')) return res;

    if (!getToken()) return res;

    logout();
    if (window.location.pathname !== '/login') {
      window.location.replace('/login');
    }
    return res;
  };
}
