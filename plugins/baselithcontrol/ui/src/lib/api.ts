import { refreshToken } from '@auth';
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
  LifecycleEvent,
  LifecycleOp,
  LogsView,
  CostUsageView,
  Me,
  MyLlmUsage,
  MyTenant,
  NewsResponse,
  Overview,
  PricingView,
  PluginRuntime,
  PluginStatus,
  QueueStatus,
  RequestVolumeSample,
  SystemResources,
  VerifyReport,
  WidgetSpec,
} from '@/types';

// All control endpoints live under the plugin's router prefix. The API is
// absolute from the site root, so it stays correct whether the SPA is served
// from /baselithcontrol/ or proxied in dev.
const API = '/api/baselithcontrol';

function url(path: string): string {
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
// Same storage keys the shared @auth context uses — a refresh performed here
// must be visible to the auth provider (and vice versa).
const TOKEN_KEY = 'auth_access_token';
const TOKEN_EXPIRY_KEY = 'auth_token_expiry';

function authHeaders(extra?: Record<string, string>): Record<string, string> {
  const token = localStorage.getItem(TOKEN_KEY);
  return {
    ...(extra ?? {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
  };
}

// ── Session-expiry handling ─────────────────────────────────────────────
// A single in-flight refresh is shared across every 401 so a burst of failing
// pollers triggers one /api/auth/refresh round-trip, not N.
let refreshInFlight: Promise<boolean> | null = null;

function refreshSession(): Promise<boolean> {
  refreshInFlight ??= refreshToken()
    .then((res) => {
      localStorage.setItem(TOKEN_KEY, res.access_token);
      localStorage.setItem(TOKEN_EXPIRY_KEY, String(Date.now() + res.expires_in * 1000));
      return true;
    })
    .catch(() => false)
    .finally(() => {
      refreshInFlight = null;
    });
  return refreshInFlight;
}

/** Drop the dead session and return to the shared login wall, then back here. */
function redirectToLogin(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(TOKEN_EXPIRY_KEY);
  // Same login route logout() uses; preserve the current path so re-login
  // returns here instead of the auth admin console.
  const target = `${window.location.pathname}${window.location.search}`;
  window.location.href = `/auth?redirect=${encodeURIComponent(target)}`;
}

interface RequestOptions extends Omit<RequestInit, 'headers'> {
  headers?: Record<string, string>;
  /**
   * Redirect to the login wall when a 401 survives the refresh+retry. The
   * fail-open auth helpers (tenants, usage, tab policy) and arbitrary widget
   * endpoints opt out so their "hide when unavailable" contract holds.
   */
  redirectOn401?: boolean;
}

/**
 * Shared authenticated fetch: Bearer + cookie credentials, one token refresh
 * and retry on 401, then a login redirect once the session is truly gone —
 * session expiry must never silently degrade the dashboard.
 */
async function request(input: string, options: RequestOptions = {}): Promise<Response> {
  const { redirectOn401 = true, headers, ...init } = options;
  // Headers are rebuilt per attempt so the retry picks up the refreshed token.
  const doFetch = () =>
    fetch(input, { credentials: 'include', ...init, headers: authHeaders(headers) });
  let res = await doFetch();
  if (res.status === 401) {
    if (await refreshSession()) res = await doFetch();
    if (res.status === 401 && redirectOn401) redirectToLogin();
  }
  return res;
}

async function getJSON<T>(path: string): Promise<T> {
  const res = await request(url(path));
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
    const res = await request('/api/auth/access/tabs', { redirectOn401: false });
    if (!res.ok) return [];
    return (await res.json()) as AccessibleTab[];
  } catch {
    return [];
  }
}

/**
 * Tenants the current user belongs to (from /api/auth/tenants). Lives under
 * /api/auth, not the control router. Fails open ([]) so the switcher simply
 * hides when auth is absent or the user has no membership.
 */
export async function fetchMyTenants(): Promise<MyTenant[]> {
  try {
    const res = await request('/api/auth/tenants', { redirectOn401: false });
    if (!res.ok) return [];
    return (await res.json()) as MyTenant[];
  } catch {
    return [];
  }
}

/**
 * The signed-in user's month-to-date LLM spend vs their effective monthly cap
 * (from /api/auth/me/llm-usage — the auth plugin owns cost governance). Lives
 * under /api/auth, not the control router. Fails open (null) so the user menu
 * simply omits the usage gauge when auth is absent or cost tracking is off.
 */
export async function fetchMyLlmUsage(): Promise<MyLlmUsage | null> {
  try {
    const res = await request('/api/auth/me/llm-usage', { redirectOn401: false });
    if (!res.ok) return null;
    return (await res.json()) as MyLlmUsage;
  } catch {
    return null;
  }
}

/**
 * Switch the active tenant: mints a fresh access token scoped to it (membership
 * verified server-side) and returns it for the caller to store.
 */
export async function switchTenant(tenantId: string): Promise<string> {
  const res = await request('/api/auth/tenants/switch', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ tenant_id: tenantId }),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  const data = (await res.json()) as { access_token: string };
  return data.access_token;
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
  const res = await request(url(`/actions/${plugin}/${op}`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
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
  const res = await request(url(`/config/${plugin}`), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
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

// Server-retained aggregate request-rate trend (survives page reloads).
export function fetchRequestVolume(): Promise<RequestVolumeSample[]> {
  return getJSON<RequestVolumeSample[]>('/resources/history');
}

// Recent plugin-lifecycle events, newest first (retained server-side).
export function fetchTimeline(limit = 50): Promise<LifecycleEvent[]> {
  return getJSON<LifecycleEvent[]>(`/timeline?limit=${limit}`);
}

// Declarative widgets fetch the plugin's own relative endpoint same-origin
// (the browser session already carries auth). The spec's endpoint is
// server-validated to be a relative path, so this never hits an external host.
export async function fetchWidgetData(endpoint: string): Promise<unknown> {
  // A plugin endpoint may 401 for its own reasons — refresh+retry, but never
  // bounce the whole dashboard to login over a single widget.
  const res = await request(endpoint, { redirectOn401: false });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

// Merged, cached public RSS/Atom headlines for the dashboard news ticker.
export function fetchNews(): Promise<NewsResponse> {
  return getJSON<NewsResponse>('/news');
}

export interface LogQuery {
  limit?: number;
  level?: string;
  plugin?: string;
  q?: string;
}

// Filtered tail of captured application logs (admin-only on the backend).
export function fetchLogs(params: LogQuery = {}): Promise<LogsView> {
  const qs = new URLSearchParams();
  if (params.limit) qs.set('limit', String(params.limit));
  if (params.level) qs.set('level', params.level);
  if (params.plugin) qs.set('plugin', params.plugin);
  if (params.q) qs.set('q', params.q);
  const suffix = qs.toString();
  return getJSON<LogsView>(`/logs${suffix ? `?${suffix}` : ''}`);
}

// LLM list-price reference table (USD per 1M tokens) for the cost panel.
export function fetchPricing(): Promise<PricingView> {
  return getJSON<PricingView>('/pricing');
}

// Real measured per-plugin LLM spend since process start (list-price cost).
export function fetchCostUsage(): Promise<CostUsageView> {
  return getJSON<CostUsageView>('/cost/usage');
}

export function streamUrl(): string {
  return url('/stream');
}

// ── CLI bridge ──────────────────────────────────────────────────────────

async function postJSON<T>(path: string): Promise<T> {
  const res = await request(url(path), { method: 'POST' });
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
