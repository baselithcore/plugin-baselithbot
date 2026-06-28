// Wire types mirroring plugins/baselithcontrol/api_models.py. Keep in sync.

export type PluginState = 'discovered' | 'active' | 'disabled' | 'failed' | 'unknown';

// "system" = framework/infrastructure plugin (manifest control.tier: system);
// "application" = custom feature plugin (default). Drives the Overview's
// collapsed "system plugins" bucket.
export type PluginTier = 'system' | 'application';

// Per-plugin tenancy model (read-only): "shared" scopes data by the
// deployment-derived tenant; "personal" forces 1 user = 1 tenant. Declared in
// the plugin manifest (PluginMetadata.tenancy); shown as an informational badge.
export type PluginTenancy = 'shared' | 'personal';

export interface EmbedSurface {
  tab_id: string;
  label: string;
  mount_url: string | null;
  static_base: string | null;
  embeddable: boolean;
}

export type StatusKind = 'healthy' | 'degraded' | 'down' | 'disabled' | 'unknown';

export interface PluginCard {
  name: string;
  version: string;
  description: string;
  category: string;
  group: string;
  tier: PluginTier;
  tenancy: PluginTenancy;
  icon: string;
  instance: string | null;
  state: PluginState;
  healthy: boolean | null;
  initialized: boolean;
  config_enabled: boolean | null;
  provides_routes: boolean;
  router_prefix: string | null;
  surfaces: EmbedSurface[];
  tags: string[];
}

export interface MetricView {
  label: string;
  value: number | string | null;
  format: string;
  tone: string;
}

export interface PluginStatus {
  plugin: string;
  kind: StatusKind;
  state: PluginState;
  latency_ms: number | null;
  code: number | null;
  last_seen: number | null;
  metrics: MetricView[];
}

export interface WidgetFieldSpec {
  path: string;
  label: string | null;
  format: string;
  highlight: Record<string, unknown> | null;
}

export interface WidgetSpec {
  plugin: string;
  title: string;
  endpoint: string;
  display: 'list' | 'block';
  fields: WidgetFieldSpec[];
}

export interface HeadStat {
  key: string;
  label: string;
  value: number;
  tone: string;
}

export interface Overview {
  api_version: string;
  total: number;
  healthy: number;
  degraded: number;
  down: number;
  embeddable: number;
  with_routes: number;
  stats: HeadStat[];
}

export interface Inventory {
  api_version: string;
  total: number;
  plugins: PluginCard[];
}

export interface ActionResult {
  plugin: string;
  operation: string;
  ok: boolean;
  state: PluginState;
  message: string;
}

export type LifecycleOp = 'enable' | 'disable' | 'reload';

export interface SystemResources {
  api_version: string;
  available: boolean;
  uptime_seconds: number;
  cpu_percent: number | null;
  host_cpu_percent: number | null;
  cpu_count: number | null;
  rss_bytes: number | null;
  rss_percent: number | null;
  mem_percent: number | null;
  mem_total_bytes: number | null;
  mem_available_bytes: number | null;
  threads: number | null;
  open_fds: number | null;
  net_sent_bps: number | null;
  net_recv_bps: number | null;
  net_sent_bytes: number | null;
  net_recv_bytes: number | null;
}

export interface PluginRuntime {
  plugin: string;
  requests: number;
  errors: number;
  in_flight: number;
  error_rate: number;
  avg_ms: number;
  p95_ms: number;
  last_ms: number;
}

// Retained aggregate request-rate series (server-side; survives reloads).
export interface RequestVolumeSample {
  timestamp: number;
  requests_per_sec: number;
}

// Retained plugin-lifecycle record for the recent-activity timeline.
export interface LifecycleEvent {
  type: string;
  timestamp: number;
  plugin: string | null;
  state: string | null;
  ok: boolean | null;
}

export interface Me {
  user_id: string;
  email?: string | null;
  username?: string | null;
  display_name?: string | null;
  roles: string[];
  is_admin: boolean;
  authenticated: boolean;
}

// One row of the central per-tab access policy (from /api/auth/access/tabs).
// `allowed` already factors in the caller's roles; `restricted=false` is open.
export interface AccessibleTab {
  plugin: string;
  tab_id: string;
  label: string;
  restricted: boolean;
  allowed: boolean;
}

// A tenant the current user belongs to (from /api/auth/tenants), for the
// app-wide tenant switcher.
export interface MyTenant {
  id: string;
  slug: string;
  name: string;
  status: string;
  role: string;
  is_default: boolean;
}

export interface ControlEvent {
  type: string;
  data: Record<string, unknown>;
}

// ── News ticker (mirrors plugins/baselithcontrol/service/news/models.py) ──

export type NewsCategory = 'ai' | 'society' | 'regulation' | 'repos' | 'tech' | 'cyber' | 'general';

export interface NewsItem {
  title: string;
  url: string;
  source: string;
  category: NewsCategory;
  published_at: number | null; // epoch seconds
  lang: string | null;
}

export interface NewsResponse {
  api_version: string;
  generated_at: number;
  count: number;
  items: NewsItem[];
  stale: boolean; // served from the last good snapshot after a refresh failure
  degraded: boolean; // no items (feeds unreachable or ticker disabled)
}

// ── CLI bridge (mirrors plugins/baselithcontrol/cli_models.py) ──────────

export interface CliCheck {
  name: string;
  passed: boolean;
  severity: string; // pass | warn | fail
  message: string;
  details: string;
}

export interface DoctorReport {
  available: boolean;
  error: string | null;
  passed: number;
  warnings: number;
  failed: number;
  elapsed_seconds: number;
  checks: CliCheck[];
}

export interface VerifyItem {
  status: string; // pass | warn | fail
  category: string;
  component: string;
  details: string;
}

export interface VerifyReport {
  available: boolean;
  error: string | null;
  passed: number;
  warnings: number;
  failed: number;
  elapsed_seconds: number;
  checks: VerifyItem[];
}

export interface InfoReport {
  available: boolean;
  error: string | null;
  framework_version: string;
  python: string;
  os: string;
  project_name: string;
  project_detected: boolean;
  plugin_count: number;
  project_path: string;
}

export interface ConfigItem {
  key: string;
  value: string;
}

export interface ConfigSection {
  name: string;
  title: string;
  available: boolean;
  error: string | null;
  items: ConfigItem[];
}

export interface ConfigReport {
  valid: boolean;
  sections: ConfigSection[];
  validation: CliCheck[];
}

export interface DbStore {
  database: string;
  online: boolean;
  message: string;
  details: string;
}

export interface DbStatus {
  available: boolean;
  error: string | null;
  stores: DbStore[];
}

export interface CacheStats {
  ok: boolean;
  error: string | null;
  total_keys: number | null;
  used_memory_human: string | null;
  peak_memory_human: string | null;
  fragmentation_ratio: string | null;
}

export interface QueueWorker {
  name: string;
  state: string;
}

export interface QueueStatus {
  available: boolean;
  error: string | null;
  workers: number;
  pending: number;
  running: number;
  completed: number;
  failed: number;
  worker_details: QueueWorker[];
}

export interface ActionOutcome {
  ok: boolean;
  message: string;
}

export type DevToolKind = 'test' | 'lint' | 'docs';

export interface JobView {
  id: string;
  kind: string;
  status: string; // running | succeeded | failed | error
  running: boolean;
  exit_code: number | null;
  started_at: number;
  ended_at: number | null;
  duration: number | null;
  command: string;
  output: string;
}
