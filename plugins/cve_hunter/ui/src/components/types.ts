/**
 * CVE Hunter TypeScript Types
 */

export interface CVSSVector {
  version: string;
  vector_string: string | null;
  base_score: number;
  exploitability_score: number | null;
  impact_score: number | null;
}

export interface AffectedProduct {
  vendor: string;
  product: string;
  versions: string[];
  cpe: string | null;
}

export interface CVEReference {
  url: string;
  source: string;
  tags: string[];
}

export type CVESeverity = 'critical' | 'high' | 'medium' | 'low' | 'none';
export type CVESource = 'nvd' | 'mitre' | 'github' | 'exploit_db' | 'discovered';
export type AgentTaskStatus = 'idle' | 'scanning' | 'analyzing' | 'discovering' | 'error';

export interface CVERecord {
  cve_id: string;
  title: string | null;
  description: string;
  severity: CVESeverity;
  cvss: CVSSVector | null;
  source: CVESource;
  published_date: string | null;
  last_modified: string | null;
  affected_products: AffectedProduct[];
  references: CVEReference[];
  cwe_ids: string[];
  exploit_available: boolean;
  patch_available: boolean;
  ai_summary: string | null;
}

export interface VulnerabilityAlert {
  alert_id: string;
  cve: CVERecord;
  alert_type: string;
  priority: number;
  created_at: string;
  acknowledged: boolean;
  acknowledged_by: string | null;
  notes: string | null;
}

export interface CVEAgentStatus {
  agent_id: string;
  agent_type: string;
  status: AgentTaskStatus;
  current_task: string | null;
  tasks_completed: number;
  tasks_failed: number;
  last_active: string | null;
  error_message: string | null;
}

export interface SwarmStatus {
  active_agents: number;
  queued_tasks: number;
  completed_tasks: number;
  failed_tasks: number;
  agents: CVEAgentStatus[];
  last_scan: string | null;
  is_scanning: boolean;
}

export interface CVEStats {
  total_cves: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  with_exploit: number;
  with_patch: number;
  discovered_today: number;
  discovered_this_week: number;
  active_alerts: number;
  sources_active: string[];
}

export interface CVEListResponse {
  items: CVERecord[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

export interface AlertListResponse {
  items: VulnerabilityAlert[];
  total: number;
  unacknowledged: number;
}
