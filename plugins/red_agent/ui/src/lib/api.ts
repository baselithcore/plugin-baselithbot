export type Severity = 'info' | 'low' | 'medium' | 'high' | 'critical';
export type FindingState = 'open' | 'triaged' | 'fixed' | 'wontfix' | 'accepted';
export type TargetKind = 'web' | 'host' | 'cloud' | 'network' | 'repo' | 'binary';
export type ScanIntensity = 'passive' | 'active' | 'intrusive';
export type EngagementStatus = 'draft' | 'active' | 'paused' | 'completed' | 'archived';
export type ScanStatus =
  | 'queued'
  | 'running'
  | 'completed'
  | 'failed'
  | 'cancelled'
  | 'awaiting_approval';

export interface Finding {
  id: string;
  scanner: string;
  title: string;
  description: string;
  severity: Severity;
  cvss_score: number | null;
  cwe: string | null;
  cve: string | null;
  target: string;
  endpoint: string | null;
  port: number | null;
  service: string | null;
  remediation: string | null;
  discovered_at: string;
  state: FindingState;
  assignee: string | null;
  triaged_at: string | null;
  resolved_at: string | null;
  due_at: string | null;
  notes: string | null;
  risk_score: number | null;
  controls: string[];
  external_ref: string | null;
  evidence?: Record<string, unknown>;
  raw?: Record<string, unknown>;
}

export type ComplianceFramework =
  | 'cis'
  | 'pci'
  | 'pci_dss_4'
  | 'nist'
  | 'nist_800_53'
  | 'iso27001'
  | 'soc2';

export interface ComplianceControl {
  count: number;
  severities: Partial<Record<Severity, number>>;
  finding_ids: string[];
}
export interface ComplianceCoverage {
  scan_id: string;
  framework: string | null;
  controls: Record<string, ComplianceControl>;
  findings_total: number;
}

export interface AutoRemediationResult {
  finding_id: string;
  pr_url: string | null;
  branch: string | null;
  fixed_version: string | null;
}

export interface ScanResult {
  scan_id: string;
  status: ScanStatus;
  started_at: string;
  finished_at: string | null;
  findings: Finding[];
  error: string | null;
  target_id: string | null;
  engagement_id: string | null;
}

export type AutonomyLevel =
  | 'observe'
  | 'plan'
  | 'recommend'
  | 'execute_passive'
  | 'execute_active'
  | 'execute_intrusive';

export interface RulesOfEngagement {
  scope_allowlist: string[];
  excluded_targets: string[];
  max_intensity: ScanIntensity;
  autonomy_level: AutonomyLevel;
  require_human_approval: boolean;
  testing_window: string | null;
  notes: string | null;
}

export interface EngagementRecord {
  id: string;
  name: string;
  objective: string;
  status: EngagementStatus;
  rules: RulesOfEngagement;
  tags: string[];
  tenant_id: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  starts_at: string | null;
  ends_at: string | null;
  archived_at: string | null;
}

export interface EngagementCreate {
  name: string;
  objective: string;
  rules?: Partial<RulesOfEngagement>;
  tags?: string[];
  starts_at?: string | null;
  ends_at?: string | null;
}

export interface EngagementUpdate {
  name?: string;
  objective?: string;
  status?: EngagementStatus;
  rules?: Partial<RulesOfEngagement>;
  tags?: string[];
  starts_at?: string | null;
  ends_at?: string | null;
}

export interface TargetRecord {
  id: string;
  kind: TargetKind;
  name: string;
  value: string;
  environment: string | null;
  owner: string | null;
  tags: string[];
  profile: Record<string, unknown>;
  schedule_cron: string | null;
  scope_overrides: Record<string, unknown>;
  description: string | null;
  tenant_id: string | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  last_scan_at: string | null;
  archived_at: string | null;
}

export interface TargetCreate {
  kind: TargetKind;
  name: string;
  value: string;
  environment?: string | null;
  owner?: string | null;
  tags?: string[];
  profile?: Record<string, unknown>;
  schedule_cron?: string | null;
  scope_overrides?: Record<string, unknown>;
  description?: string | null;
}

export interface TargetUpdate {
  name?: string;
  environment?: string | null;
  owner?: string | null;
  tags?: string[];
  profile?: Record<string, unknown>;
  schedule_cron?: string | null;
  scope_overrides?: Record<string, unknown>;
  description?: string | null;
  archived?: boolean;
}

export interface TargetPosture {
  severity_counts: Partial<Record<Severity, number>>;
  state_counts: Partial<Record<FindingState, number>>;
  overdue: number;
  scans_total: number;
  scans_completed: number;
  scans_failed: number;
  last_scan_at: string | null;
  histogram: { day: string; severity: Severity; count: number }[];
}

export interface FindingTriageUpdate {
  state?: FindingState;
  assignee?: string | null;
  notes?: string | null;
  due_at?: string | null;
}

export interface ActivityEvent {
  id: number;
  scan_id: string | null;
  actor: string | null;
  event: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface FindingEvidence {
  finding: Finding;
  scan_id: string;
  chain: {
    id: number;
    actor: string | null;
    event: string;
    payload: Record<string, unknown>;
    created_at: string | null;
  }[];
}

export interface RunDiffRegression {
  finding: Finding;
  from_severity: Severity;
  to_severity: Severity;
}

export interface RunDiff {
  baseline_scan_id: string;
  latest_scan_id: string;
  new: Finding[];
  fixed: Finding[];
  regressed: RunDiffRegression[];
  unchanged: number;
}

const TOKEN_KEY = 'red_agent.token';
export const getToken = () => localStorage.getItem(TOKEN_KEY) ?? '';
export const setToken = (t: string) => localStorage.setItem(TOKEN_KEY, t);

async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
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

export interface ScanRow {
  id: string;
  status: ScanStatus;
  target_value: string;
  target_id: string | null;
  engagement_id: string | null;
  intensity: ScanIntensity;
  scanners: string[];
  requested_by: string;
  started_at: string;
  finished_at: string | null;
  error: string | null;
}

export interface CyNode {
  data: {
    id: string;
    label: string;
    display: string;
    severity: Severity | null;
    cvss: number | null;
  };
}
export interface CyEdge {
  data: { id: string; source: string; target: string; type: string };
}
export interface AttackSurfaceResp {
  nodes: CyNode[];
  edges: CyEdge[];
}

export interface FindingFilters {
  severity?: Severity;
  cwe?: string;
  scanner?: string;
  target?: string;
  target_id?: string;
  state?: FindingState;
  assignee?: string;
  overdue?: boolean;
  limit?: number;
  offset?: number;
}

export interface TargetListFilters {
  kind?: TargetKind;
  environment?: string;
  include_archived?: boolean;
  limit?: number;
  offset?: number;
}

function qs(params: Record<string, string | number | undefined>): string {
  const usp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== '') usp.set(k, String(v));
  }
  const s = usp.toString();
  return s ? `?${s}` : '';
}

function qsLoose(filters: Record<string, unknown>): string {
  const cleaned: Record<string, string | number | undefined> = {};
  for (const [k, v] of Object.entries(filters)) {
    if (v === undefined || v === null || v === '' || v === false) continue;
    cleaned[k] = typeof v === 'boolean' ? String(v) : (v as string | number);
  }
  return qs(cleaned);
}

export const api = {
  getScan: (id: string) => call<ScanResult>(`/red-agent/scans/${id}`),
  listScans: (
    filters: {
      status_filter?: string;
      target_id?: string;
      engagement_id?: string;
      limit?: number;
      offset?: number;
    } = {}
  ) => call<ScanRow[]>(`/red-agent/scans${qsLoose(filters)}`),
  listEngagements: (
    filters: {
      status_filter?: EngagementStatus;
      include_archived?: boolean;
      limit?: number;
      offset?: number;
    } = {}
  ) =>
    call<EngagementRecord[]>(
      `/red-agent/engagements${qsLoose(filters as Record<string, unknown>)}`
    ),
  getEngagement: (id: string) => call<EngagementRecord>(`/red-agent/engagements/${id}`),
  createEngagement: (body: EngagementCreate) =>
    call<EngagementRecord>('/red-agent/engagements', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  updateEngagement: (id: string, body: EngagementUpdate) =>
    call<EngagementRecord>(`/red-agent/engagements/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),
  archiveEngagement: (id: string) =>
    call<void>(`/red-agent/engagements/${id}`, { method: 'DELETE' }),
  quickScan: (target: string) =>
    call<{ scan_id: string }>(`/red-agent/scans/quick?target_value=${encodeURIComponent(target)}`, {
      method: 'POST',
    }),
  listFindings: (filters: FindingFilters = {}) =>
    call<Finding[]>(`/red-agent/findings${qsLoose(filters as Record<string, unknown>)}`),
  getAttackSurface: (target: string) =>
    call<AttackSurfaceResp>(`/red-agent/graph/attack-surface?target=${encodeURIComponent(target)}`),
  getFindingGraph: (findingId: string, depth: number = 2) =>
    call<AttackSurfaceResp>(
      `/red-agent/graph/finding/${encodeURIComponent(findingId)}?depth=${depth}`
    ),
  exportSarif: (scanId: string) => call<unknown>(`/red-agent/reports/${scanId}/sarif`),
  exportOcsf: (scanId: string) => call<unknown>(`/red-agent/reports/${scanId}/ocsf`),
  scanSigmaBundleUrl: (scanId: string) => `/red-agent/reports/${scanId}/sigma.zip`,
  engagementSigmaBundleUrl: (engagementId: string) =>
    `/red-agent/engagements/${engagementId}/sigma.zip`,
  findingSigmaUrlWithOverrides: (
    id: string,
    opts: { keywords?: string[]; tags?: string[] } = {}
  ) => {
    const usp = new URLSearchParams();
    for (const k of opts.keywords ?? []) {
      const t = k.trim();
      if (t) usp.append('keyword', t);
    }
    for (const t of opts.tags ?? []) {
      const tt = t.trim();
      if (tt) usp.append('tag', tt);
    }
    const q = usp.toString();
    return `/red-agent/findings/${id}/sigma${q ? `?${q}` : ''}`;
  },
  exportCompliance: (scanId: string, framework?: ComplianceFramework) =>
    call<ComplianceCoverage>(
      `/red-agent/reports/${scanId}/compliance${framework ? `?framework=${framework}` : ''}`
    ),
  autoRemediateFinding: (id: string) =>
    call<AutoRemediationResult>(`/red-agent/findings/${id}/auto-remediate`, { method: 'POST' }),
  getFindingEvidence: (id: string, chainLimit = 500) =>
    call<FindingEvidence>(`/red-agent/findings/${id}/evidence?chain_limit=${chainLimit}`),
  findingSigmaUrl: (id: string) => `/red-agent/findings/${id}/sigma`,
  governanceStats: (opts: { sinceHours?: number; engagementId?: string } = {}) => {
    const usp = new URLSearchParams();
    usp.set('since_hours', String(opts.sinceHours ?? 24));
    if (opts.engagementId) usp.set('engagement_id', opts.engagementId);
    return call<{
      window_hours: number;
      counts: Record<string, number>;
      totals: {
        violations: number;
        adjustments: number;
        hitl_timeouts: number;
      };
    }>(`/red-agent/activity/governance-stats?${usp.toString()}`);
  },
  governanceTrend: (
    opts: {
      sinceHours?: number;
      bucket?: 'minute' | 'hour' | 'day';
      engagementId?: string;
    } = {}
  ) => {
    const usp = new URLSearchParams();
    usp.set('since_hours', String(opts.sinceHours ?? 24));
    usp.set('bucket', opts.bucket ?? 'hour');
    if (opts.engagementId) usp.set('engagement_id', opts.engagementId);
    return call<{
      window_hours: number;
      bucket: string;
      series: {
        ts: string;
        violations: number;
        adjustments: number;
        hitl_timeouts: number;
      }[];
    }>(`/red-agent/activity/governance-trend?${usp.toString()}`);
  },
  listActivity: (
    opts: {
      cockpit?: boolean;
      eventPrefix?: string[];
      limit?: number;
      engagementId?: string;
    } = {}
  ) => {
    const usp = new URLSearchParams();
    if (opts.cockpit) usp.set('cockpit', 'true');
    if (opts.limit) usp.set('limit', String(opts.limit));
    if (opts.engagementId) usp.set('engagement_id', opts.engagementId);
    for (const p of opts.eventPrefix ?? []) usp.append('event_prefix', p);
    const q = usp.toString();
    return call<ActivityEvent[]>(`/red-agent/activity${q ? `?${q}` : ''}`);
  },
  preflight: (body: PreflightBody) =>
    call<PreflightResp>('/red-agent/guardrails/preflight', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  createScan: (body: CreateScanBody) =>
    call<{ scan_id: string }>('/red-agent/scans', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  approveScan: (id: string) =>
    call<{ status: string }>(`/red-agent/scans/${id}/approve`, { method: 'POST' }),
  rejectScan: (id: string) =>
    call<{ status: string }>(`/red-agent/scans/${id}/reject`, { method: 'POST' }),
  cancelScan: (id: string) =>
    call<{ status: string }>(`/red-agent/scans/${id}/cancel`, { method: 'POST' }),
  deleteScan: (id: string) => call<void>(`/red-agent/scans/${id}`, { method: 'DELETE' }),

  // ── Targets (project-as-entity) ────────────────────────────────────
  listTargets: (filters: TargetListFilters = {}) =>
    call<TargetRecord[]>(`/red-agent/targets${qsLoose(filters as Record<string, unknown>)}`),
  getTarget: (id: string) => call<TargetRecord>(`/red-agent/targets/${id}`),
  getTargetPosture: (id: string) => call<TargetPosture>(`/red-agent/targets/${id}/posture`),
  listTargetScans: (id: string, opts: { limit?: number; offset?: number } = {}) =>
    call<ScanRow[]>(`/red-agent/targets/${id}/scans${qsLoose(opts as Record<string, unknown>)}`),
  listTargetActivity: (id: string, limit = 100) =>
    call<ActivityEvent[]>(`/red-agent/targets/${id}/activity?limit=${limit}`),
  diffRuns: (targetId: string, baseline: string, latest: string) =>
    call<RunDiff>(
      `/red-agent/targets/${targetId}/diff?baseline=${encodeURIComponent(baseline)}&latest=${encodeURIComponent(latest)}`
    ),
  createTarget: (body: TargetCreate) =>
    call<TargetRecord>('/red-agent/targets', { method: 'POST', body: JSON.stringify(body) }),
  updateTarget: (id: string, body: TargetUpdate) =>
    call<TargetRecord>(`/red-agent/targets/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),
  launchTargetScan: (
    id: string,
    body: {
      scanners?: string[];
      engagement_id?: string | null;
      intensity?: ScanIntensity;
      notes?: string;
    } = {}
  ) =>
    call<{ scan_id: string; target_id: string }>(`/red-agent/targets/${id}/scans`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  deleteTarget: (id: string, opts: { hard?: boolean; purgeRuns?: boolean } = {}) => {
    const q = qs({
      hard: opts.hard ? 'true' : undefined,
      purge_runs: opts.purgeRuns ? 'true' : undefined,
    });
    return call<void>(`/red-agent/targets/${id}${q}`, { method: 'DELETE' });
  },

  // ── Binary / file scans ───────────────────────────────────────────
  uploadFileForScan: async (
    file: File,
    opts: { engagementId?: string; notes?: string } = {}
  ): Promise<{ scan_id: string; sha256: string; size: number; filename: string }> => {
    const form = new FormData();
    form.append('file', file);
    if (opts.engagementId) form.append('engagement_id', opts.engagementId);
    if (opts.notes) form.append('notes', opts.notes);
    const res = await fetch('/red-agent/file-scans', {
      method: 'POST',
      headers: { Authorization: `Bearer ${getToken()}` },
      body: form,
    });
    if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
    return res.json();
  },
  getSampleInfo: (sha256: string) =>
    call<{ sha256: string; available: boolean; files?: string[] }>(
      `/red-agent/file-scans/${sha256}/info`
    ),
  purgeSample: (sha256: string) =>
    call<void>(`/red-agent/file-scans/${sha256}`, { method: 'DELETE' }),

  // ── Finding triage ────────────────────────────────────────────────
  updateFinding: (id: string, body: FindingTriageUpdate) =>
    call<{ finding_id: string; status: string }>(`/red-agent/findings/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(body),
    }),

  // ── Fleet (endpoint daemons) ──────────────────────────────────────
  listFleet: (
    filters: {
      status_filter?: AgentStatus;
      os?: AgentOS;
      limit?: number;
      offset?: number;
    } = {}
  ) => call<AgentSummary[]>(`/red-agent/agents${qsLoose(filters as Record<string, unknown>)}`),
  getAgent: (uuid: string) => call<AgentDetail>(`/red-agent/agents/${uuid}`),
  listAgentTelemetry: (uuid: string, opts: { kind?: string; limit?: number } = {}) =>
    call<AgentTelemetryRow[]>(
      `/red-agent/agents/${uuid}/telemetry${qsLoose(opts as Record<string, unknown>)}`
    ),
  listFleetTelemetry: (opts: { kind?: string; limit?: number } = {}) =>
    call<AgentTelemetryRow[]>(
      `/red-agent/agents/telemetry${qsLoose(opts as Record<string, unknown>)}`
    ),
  createEnrollmentToken: (body: {
    ttl_seconds?: number;
    bind_agent_uuid?: string;
    labels?: Record<string, unknown>;
  }) =>
    call<EnrollmentTokenIssued>('/red-agent/agents/enrollment-tokens', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
};

// ── Fleet types ───────────────────────────────────────────────────
export type AgentOS = 'linux' | 'macos' | 'windows';
export type AgentStatus = 'enrolled' | 'online' | 'offline' | 'revoked' | 'disabled';

export interface AgentSummary {
  agent_uuid: string;
  tenant_id: string;
  os: AgentOS;
  arch: string;
  hostname: string | null;
  status: AgentStatus;
  daemon_version: string | null;
  capabilities: string[];
  labels: Record<string, unknown>;
  last_seen_at: string | null;
  enrolled_at: string;
}

export interface AgentDetail extends AgentSummary {
  os_version: string | null;
  kernel_version: string | null;
  cpu_count: number | null;
  mem_total_bytes: number | null;
  protocol_version: number;
  enrolled_by: string | null;
  archived_at: string | null;
  last_disconnect_reason: string | null;
}

export interface AgentTelemetryRow {
  id: string;
  agent_uuid: string;
  observed_at: string;
  received_at: string;
  kind: string;
  severity: Severity;
  attributes: Record<string, unknown>;
  correlation_id: string | null;
  batch_id: string;
}

export interface EnrollmentTokenIssued {
  id: string;
  token: string;
  tenant_id: string;
  expires_at: string;
  bind_agent_uuid: string | null;
}

export type PreflightTargetType =
  | 'url'
  | 'hostname'
  | 'ip'
  | 'cidr'
  | 'repo'
  | 'iac'
  | 'cloud_account'
  | 'k8s_cluster'
  | 'api_spec'
  | 'binary'
  | 'system';

export interface PreflightBody {
  target: { type: PreflightTargetType; value: string };
  scanners: string[];
  intensity: 'passive' | 'active' | 'intrusive';
}
export interface PreflightResp {
  allowed: boolean;
  needs_human_approval: boolean;
  reason: string;
  violations: string[];
  target_violation: string | null;
  target_violation_message: string | null;
}
export interface CreateScanBody {
  target: PreflightBody['target'];
  engagement_id?: string | null;
  scanners: string[];
  intensity: PreflightBody['intensity'];
  bug_bounty_program?: string | null;
  notes?: string | null;
}

export function openScanStream(scanId: string): WebSocket {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  return new WebSocket(
    `${proto}://${location.host}/red-agent/ws/scans/${scanId}?token=${encodeURIComponent(getToken())}`
  );
}

export function openActivityStream(
  opts: { eventPrefix?: string[]; engagementId?: string } = {}
): WebSocket {
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const usp = new URLSearchParams();
  usp.set('token', getToken());
  for (const p of opts.eventPrefix ?? []) {
    if (p) usp.append('event_prefix', p);
  }
  if (opts.engagementId) usp.set('engagement_id', opts.engagementId);
  return new WebSocket(`${proto}://${location.host}/red-agent/ws/activity?${usp.toString()}`);
}
