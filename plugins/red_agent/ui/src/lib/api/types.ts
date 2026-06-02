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
