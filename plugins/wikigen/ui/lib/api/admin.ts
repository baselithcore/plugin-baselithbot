import { ApiError, BASE, json } from './client';
import { postFormWithProgress, type UploadOptions } from './_upload';

export interface ScaffoldDefaults {
  languages: string[];
  suggested_page_types: { id: string; label: string }[];
  template_label: string;
  template_description: string;
}

export interface TenantInfo {
  name: string;
  label: string;
  description: string;
  language: string;
  page_types: string[];
  pack_dir: string;
  valid: boolean;
  error: string | null;
  is_active: boolean;
  is_seed: boolean;
}

export interface TenantListResponse {
  count: number;
  active: string | null;
  tenants: TenantInfo[];
}

export interface ScaffoldRequestBody {
  name: string;
  label?: string;
  description?: string;
  language: string;
  vault_root?: string;
  write_env: boolean;
  force?: boolean;
  activate?: boolean;
  from_seed?: string | null;
  synthesize_prompts?: boolean;
  provider?: {
    vendor?: 'ollama' | 'openai';
    rag_vendor?: 'ollama' | 'openai';
    ingest_vendor?: 'ollama' | 'openai';
    model?: string;
    ingest_model?: string;
    base_url?: string;
    api_key?: string;
    ollama_url?: string;
    openai_api_base?: string;
    openai_api_key?: string;
  } | null;
}

export interface ScaffoldPlanResponse {
  name: string;
  label: string;
  description: string;
  language: string;
  target_pack_dir: string;
  vault_path: string;
  will_overwrite: boolean;
  pack_dir_exists: boolean;
  operations: { kind: string; target: string; note: string }[];
  env_diff: { key: string; value: string }[];
  next_steps: string[];
}

export interface ScaffoldResultResponse {
  name: string;
  target_pack_dir: string;
  vault_path: string;
  env_written: boolean;
  env_path: string | null;
  activated: boolean;
  requires_restart: boolean;
  next_steps: string[];
  synthesis_applied?: boolean;
  synthesis_model?: string | null;
  synthesis_warning?: string | null;
}

export interface ActivateResponse {
  name: string;
  requires_restart: boolean;
  env_path: string | null;
  written: boolean;
}

export function fetchScaffoldDefaults(signal?: AbortSignal): Promise<ScaffoldDefaults> {
  return json<ScaffoldDefaults>('/admin/scaffold/defaults', { signal });
}

export function fetchTenants(refresh = false, signal?: AbortSignal): Promise<TenantListResponse> {
  return json<TenantListResponse>(`/admin/tenants${refresh ? '?refresh=true' : ''}`, { signal });
}

export function previewScaffold(
  body: ScaffoldRequestBody,
  signal?: AbortSignal
): Promise<ScaffoldPlanResponse> {
  return json<ScaffoldPlanResponse>('/admin/scaffold/preview', {
    method: 'POST',
    body: JSON.stringify(body),
    signal,
  });
}

export function applyScaffold(
  body: ScaffoldRequestBody,
  signal?: AbortSignal
): Promise<ScaffoldResultResponse> {
  return json<ScaffoldResultResponse>('/admin/scaffold', {
    method: 'POST',
    body: JSON.stringify(body),
    signal,
  });
}

export function activateTenant(name: string, signal?: AbortSignal): Promise<ActivateResponse> {
  return json<ActivateResponse>(`/admin/tenants/${encodeURIComponent(name)}/activate`, {
    method: 'POST',
    signal,
  });
}

// --- obsidian per-tenant gating -------------------------------------------

export interface ObsidianStateResponse {
  name: string;
  enabled: boolean;
  initialized_at: string | null;
  initialized_by: string | null;
}

export function fetchObsidianState(
  tenant: string,
  signal?: AbortSignal
): Promise<ObsidianStateResponse> {
  return json<ObsidianStateResponse>(
    `/admin/tenants/${encodeURIComponent(tenant)}/obsidian`,
    { signal }
  );
}

export function initObsidian(
  tenant: string,
  signal?: AbortSignal
): Promise<ObsidianStateResponse> {
  return json<ObsidianStateResponse>(
    `/admin/tenants/${encodeURIComponent(tenant)}/obsidian/init`,
    { method: 'POST', signal }
  );
}

export function disableObsidian(
  tenant: string,
  signal?: AbortSignal
): Promise<ObsidianStateResponse> {
  return json<ObsidianStateResponse>(
    `/admin/tenants/${encodeURIComponent(tenant)}/obsidian/disable`,
    { method: 'POST', signal }
  );
}

// per-tenant branding/asset uploads (wizard "Branding" + "Documenti" steps)

export interface TenantUploadResponse {
  name: string;
  filename: string;
  size: number;
  target_path: string;
}

export function uploadTenantRaw(
  tenant: string,
  file: File,
  opts: { overwrite?: boolean } = {},
  uploadOpts: UploadOptions = {}
): Promise<TenantUploadResponse> {
  const fd = new FormData();
  fd.append('file', file);
  if (opts.overwrite !== undefined) fd.append('overwrite', String(opts.overwrite));
  return postFormWithProgress<TenantUploadResponse>(
    `/admin/tenants/${encodeURIComponent(tenant)}/raw`,
    fd,
    uploadOpts
  );
}

export function uploadTenantLogo(
  tenant: string,
  file: File,
  uploadOpts: UploadOptions = {}
): Promise<TenantUploadResponse> {
  const fd = new FormData();
  fd.append('file', file);
  return postFormWithProgress<TenantUploadResponse>(
    `/admin/tenants/${encodeURIComponent(tenant)}/logo`,
    fd,
    uploadOpts
  );
}

export interface ThemeUpdateBody {
  primary?: string;
  primary_hover?: string;
  accent?: string;
}

export function updateTenantTheme(
  tenant: string,
  body: ThemeUpdateBody,
  signal?: AbortSignal
): Promise<{ name: string; theme: ThemeUpdateBody }> {
  return json(`/admin/tenants/${encodeURIComponent(tenant)}/theme`, {
    method: 'POST',
    body: JSON.stringify(body),
    signal,
  });
}

// --- per-tenant branding edit (text + suggested questions) ------------------

export interface TenantSuggestedQuestion {
  label: string;
  prompt: string;
  hint?: string;
  category?: string;
  icon?: string | null;
}

export interface TenantBrandingPayload {
  name: string;
  label: string;
  description: string;
  ui: {
    app_name?: string;
    short_name?: string | null;
    vault_label?: string;
    tagline?: string | null;
    empty_state?: string | null;
    hero_question?: string | null;
    hero_highlight?: string | null;
    hero_pill?: string | null;
    hero_pill_icon?: string | null;
    disclaimer?: string | null;
    suggested_questions?: TenantSuggestedQuestion[];
    [k: string]: unknown;
  };
}

export interface TenantBrandingUpdateBody {
  label?: string;
  description?: string;
  app_name?: string;
  short_name?: string;
  vault_label?: string;
  tagline?: string;
  empty_state?: string;
  hero_question?: string;
  hero_highlight?: string;
  hero_pill?: string;
  hero_pill_icon?: string;
  disclaimer?: string;
  suggested_questions?: TenantSuggestedQuestion[];
}

export function fetchTenantBranding(
  tenant: string,
  signal?: AbortSignal
): Promise<TenantBrandingPayload> {
  return json<TenantBrandingPayload>(
    `/admin/tenants/${encodeURIComponent(tenant)}/branding`,
    { signal }
  );
}

export function updateTenantBranding(
  tenant: string,
  body: TenantBrandingUpdateBody,
  signal?: AbortSignal
): Promise<TenantBrandingPayload> {
  return json<TenantBrandingPayload>(
    `/admin/tenants/${encodeURIComponent(tenant)}/branding`,
    {
      method: 'PUT',
      body: JSON.stringify(body),
      signal,
    }
  );
}

export interface RestartResponse {
  scheduled: boolean;
  pid: number;
  delay_ms: number;
  note: string;
  requires_manual?: boolean;
  mode?: 'reload' | 'supervised' | 'bare' | 'unknown';
}

export function restartBackend(
  delay_ms = 500,
  signal?: AbortSignal
): Promise<RestartResponse> {
  return json<RestartResponse>(`/admin/restart?delay_ms=${delay_ms}`, {
    method: 'POST',
    signal,
  });
}

export interface ActivateNowResponse {
  ok: boolean;
  pack: string | null;
  setup_mode: boolean;
  jobs_started: number;
  note: string;
}

/**
 * Bare-mode soft activation: replays lifespan side-effects (load pack,
 * warm embedder, create qdrant collection, autostart pending ingest)
 * in-process. Called by the wizard when /admin/restart returns
 * `requires_manual: true, mode: 'bare'` — instead of demanding a
 * terminal restart we activate the new pack in the running worker.
 */
export function activateNow(signal?: AbortSignal): Promise<ActivateNowResponse> {
  return json<ActivateNowResponse>(`/admin/activate-now`, {
    method: 'POST',
    signal,
  });
}

export interface ProviderUpdateRequest {
  vendor?: 'ollama' | 'openai';
  rag_vendor?: 'ollama' | 'openai';
  ingest_vendor?: 'ollama' | 'openai';
  model?: string;
  ingest_model?: string;
  base_url?: string;
  api_key?: string;
  ollama_url?: string;
  openai_api_base?: string;
  openai_api_key?: string;
}

export interface ProviderUpdateResponse {
  ok: boolean;
  vendor: string | null;
  rag_vendor: string | null;
  ingest_vendor: string | null;
  model: string | null;
  ingest_model: string | null;
  base_url: string | null;
  env_written: boolean;
  note: string;
}

/**
 * Rotate LLM provider config on an already-scaffolded tenant. Writes the
 * keys to `.env`, mirrors them into the live process env, refreshes
 * module-level config constants, and resets cached LLM clients so the
 * next inference call picks up the new vendor / key / url without a
 * server restart.
 */
export function updateProvider(
  body: ProviderUpdateRequest,
  signal?: AbortSignal
): Promise<ProviderUpdateResponse> {
  return json<ProviderUpdateResponse>(`/admin/provider`, {
    method: 'POST',
    body: JSON.stringify(body),
    signal,
  });
}

export interface RuntimeProbe {
  domain: string;
  setup_mode: boolean;
  boot_id?: string;
  boot_at?: number;
}

/**
 * One-shot probe of /api/branding. Used by the wizard to capture the
 * current `boot_id` BEFORE triggering a restart, so it can wait for
 * the post-restart worker to come up (different boot_id).
 */
export async function probeBackend(signal?: AbortSignal): Promise<RuntimeProbe> {
  const r = await fetch(`${BASE}/branding`, { signal });
  if (!r.ok) throw new ApiError(r.status, await r.text().catch(() => r.statusText));
  return (await r.json()) as RuntimeProbe;
}

/**
 * Polls /api/branding until it reports an active domain (post-restart).
 * When `expectBootIdNot` is provided, also waits until the reported
 * `boot_id` differs — proves the worker actually rebooted instead of
 * just returning the new tenant after `os.environ` was mutated in-place.
 * Resolves with the live branding payload, rejects after `timeoutMs`.
 */
export class StaleBootIdError extends Error {
  constructor() {
    super('backend reachable but boot_id unchanged — restart did not occur');
    this.name = 'StaleBootIdError';
  }
}

export async function pollBackendUp(
  timeoutMs = 60_000,
  intervalMs = 1500,
  expectBootIdNot?: string,
  signal?: AbortSignal
): Promise<RuntimeProbe> {
  const deadline = Date.now() + timeoutMs;
  // If backend keeps replying 200 with the SAME boot_id we captured pre-restart,
  // the worker never died. After a few seconds of that we fail fast — no point
  // waiting the full timeout on a process that won't reboot.
  const staleAfterMs = 8_000;
  let firstSeenStaleAt: number | null = null;
  let lastErr: unknown = null;
  while (Date.now() < deadline) {
    if (signal?.aborted) throw new Error('aborted');
    try {
      const r = await fetch(`${BASE}/branding`, { signal });
      if (r.ok) {
        const body = (await r.json()) as RuntimeProbe;
        const ready = body.domain && !body.setup_mode;
        const restarted = !expectBootIdNot || (!!body.boot_id && body.boot_id !== expectBootIdNot);
        if (ready && restarted) return body;
        if (expectBootIdNot && body.boot_id === expectBootIdNot) {
          if (firstSeenStaleAt == null) firstSeenStaleAt = Date.now();
          else if (Date.now() - firstSeenStaleAt >= staleAfterMs) {
            throw new StaleBootIdError();
          }
        } else {
          firstSeenStaleAt = null;
        }
      }
    } catch (err) {
      if (err instanceof StaleBootIdError) throw err;
      lastErr = err;
    }
    await new Promise((res) => setTimeout(res, intervalMs));
  }
  throw lastErr ?? new Error('backend not back up within timeout');
}
