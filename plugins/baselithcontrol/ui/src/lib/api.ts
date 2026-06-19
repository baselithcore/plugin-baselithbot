import type {
  AccessibleTab,
  ActionOutcome,
  ActionResult,
  CacheStats,
  ConfigReport,
  DbStatus,
  DevToolKind,
  DoctorReport,
  Inventory,
  InfoReport,
  JobView,
  LifecycleOp,
  Me,
  Overview,
  PluginRuntime,
  PluginStatus,
  QueueStatus,
  SystemResources,
  VerifyReport,
  WidgetSpec,
} from '@/types';

// All control endpoints live under the plugin's router prefix. The Vite `base`
// keeps this correct whether served from /baselithcontrol/ or proxied in dev.
const BASE = `${import.meta.env.BASE_URL.replace(/\/$/, '')}`;
const API = '/api/baselithcontrol';

function url(path: string): string {
  // In production the SPA is served from /baselithcontrol/; the API is absolute
  // from the site root, so we do not prefix it with BASE.
  void BASE;
  return `${API}${path}`;
}

/**
 * Bearer header from the shared auth access token (same localStorage key the
 * `@auth` context uses). REQUIRED for impersonation to be honored: an admin's
 * impersonation mints a target-scoped access token in localStorage but leaves
 * the admin's refresh cookie untouched (RFC 8693). Cookie-only requests would
 * therefore still resolve as the admin — so `/me` and `/access/tabs` must carry
 * the Bearer to reflect the impersonated identity (and its restricted tabs).
 * Falls back to cookie auth when no token is present.
 */
function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const token = localStorage.getItem('auth_access_token');
  return {
    ...(extra ?? {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(url(path), { credentials: 'include', headers: authHeaders() });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return (await res.json()) as T;
}

export function fetchInventory(): Promise<Inventory> {
  return getJSON<Inventory>('/inventory');
}

/**
 * Fetch the caller's per-tab access policy from the central auth plugin.
 * Lives under /api/auth (not the control router), so the path is absolute.
 * Returns [] when auth is absent/unauthenticated so the UI fails open.
 */
export async function fetchAccessibleTabs(): Promise<AccessibleTab[]> {
  try {
    const res = await fetch('/api/auth/access/tabs', {
      credentials: 'include',
      headers: authHeaders(),
    });
    if (!res.ok) return [];
    return (await res.json()) as AccessibleTab[];
  } catch {
    return [];
  }
}

export function fetchStatus(): Promise<{
  healthy: boolean;
  plugins: Record<string, Record<string, unknown>>;
  metrics: Record<string, unknown>;
}> {
  return getJSON('/status');
}

export async function runAction(
  plugin: string,
  op: LifecycleOp,
  reason?: string
): Promise<ActionResult> {
  const res = await fetch(url(`/actions/${plugin}/${op}`), {
    method: 'POST',
    credentials: 'include',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ reason: reason ?? null }),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return (await res.json()) as ActionResult;
}

export async function setPluginConfig(
  plugin: string,
  enabled: boolean,
  reason?: string
): Promise<ActionResult> {
  const res = await fetch(url(`/config/${plugin}`), {
    method: 'POST',
    credentials: 'include',
    headers: authHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ enabled, reason: reason ?? null }),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return (await res.json()) as ActionResult;
}

export function fetchMe(): Promise<Me> {
  return getJSON<Me>('/me');
}

/**
 * Log out of the shared auth session, then return to the auth console login.
 * Hits the central auth plugin (clears the refresh cookie) — same origin.
 */
export async function logout(): Promise<void> {
  try {
    await fetch('/api/auth/logout', { method: 'POST', credentials: 'include' });
  } finally {
    // The auth SPA is served via StaticFiles (no deep-link fallback), so target
    // its mount root ('/auth'): it boots and renders the login page when the
    // session is gone. '/auth/login' would 404 (not a real static file).
    // Pass redirect so re-login returns here instead of the auth admin console.
    window.location.href = '/auth?redirect=/baselithcontrol/';
  }
}

export function fetchOverview(): Promise<Overview> {
  return getJSON<Overview>('/overview');
}

export function fetchWidgets(): Promise<WidgetSpec[]> {
  return getJSON<WidgetSpec[]>('/widgets');
}

export function fetchPluginStatus(plugin: string): Promise<PluginStatus> {
  return getJSON<PluginStatus>(`/status/${plugin}`);
}

export function fetchResources(): Promise<SystemResources> {
  return getJSON<SystemResources>('/resources');
}

export function fetchPluginRuntime(): Promise<PluginRuntime[]> {
  return getJSON<PluginRuntime[]>('/resources/plugins');
}

// Declarative widgets fetch the plugin's own relative endpoint same-origin
// (the browser session already carries auth). The spec's endpoint is
// server-validated to be a relative path, so this never hits an external host.
export async function fetchWidgetData(endpoint: string): Promise<unknown> {
  const res = await fetch(endpoint, { credentials: 'include', headers: authHeaders() });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export function streamUrl(): string {
  return url('/stream');
}

// ── CLI bridge ──────────────────────────────────────────────────────────

async function postJSON<T>(path: string): Promise<T> {
  const res = await fetch(url(path), {
    method: 'POST',
    credentials: 'include',
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return (await res.json()) as T;
}

export const fetchDoctor = (): Promise<DoctorReport> => getJSON<DoctorReport>('/cli/doctor');
export const fetchVerify = (): Promise<VerifyReport> => getJSON<VerifyReport>('/cli/verify');
export const fetchInfo = (): Promise<InfoReport> => getJSON<InfoReport>('/cli/info');
export const fetchConfigReport = (): Promise<ConfigReport> => getJSON<ConfigReport>('/cli/config');

export const fetchDbStatus = (): Promise<DbStatus> => getJSON<DbStatus>('/cli/infra/db');
export const fetchCacheStats = (): Promise<CacheStats> => getJSON<CacheStats>('/cli/infra/cache');
export const fetchQueueStatus = (): Promise<QueueStatus> =>
  getJSON<QueueStatus>('/cli/infra/queue');

export const clearCache = (): Promise<ActionOutcome> =>
  postJSON<ActionOutcome>('/cli/infra/cache/clear');
export const resetDb = (): Promise<ActionOutcome> => postJSON<ActionOutcome>('/cli/infra/db/reset');

export const runDevTool = (kind: DevToolKind): Promise<JobView> =>
  postJSON<JobView>(`/cli/devtools/${kind}`);
export const fetchJobs = (): Promise<JobView[]> => getJSON<JobView[]>('/cli/devtools/jobs');
export const fetchJob = (id: string): Promise<JobView> =>
  getJSON<JobView>(`/cli/devtools/jobs/${id}`);
