/**
 * Core event and session related types
 */

export type HoneypotProtocol = 'ssh' | 'http' | 'tcp';
export type AttackSeverity = 'critical' | 'high' | 'medium' | 'low' | 'info';
export type AttackCategory =
  | 'brute_force'
  | 'sql_injection'
  | 'command_injection'
  | 'path_traversal'
  | 'xss'
  | 'reconnaissance'
  | 'credential_harvesting'
  | 'malware_delivery'
  | 'unknown';

export interface GeoLocation {
  country: string | null;
  country_code: string | null;
  city: string | null;
  latitude: number | null;
  longitude: number | null;
  isp?: string | null;
}

export interface BotDetectionSignals {
  inter_request_interval_ms: number | null;
  request_rate_per_minute: number | null;
  session_duration_ms: number | null;
  payload_entropy: number | null;
  pattern_repetition_score: number | null;
  timing_variance: number | null;
}

export interface AttackEvent {
  event_id: string;
  session_id: string;
  honeypot_id: string;
  protocol: HoneypotProtocol;
  timestamp: string;
  source_ip: string;
  source_port: number;
  geo: GeoLocation | null;
  event_type: string;
  raw_data: string;
  username: string | null;
  password: string | null;
  command: string | null;
  http_method: string | null;
  http_path: string | null;
  http_headers: Record<string, string> | null;
  http_body: string | null;
  detected_patterns: string[];
  category: AttackCategory;
  severity: AttackSeverity;
  ai_classification: string | null;
  matched_cves: string[];
  matched_cwes: string[];
  correlation_confidence: number | null;
  is_bot: boolean | null;
  bot_confidence: number | null;
  bot_classification: 'bot' | 'human' | 'unknown' | null;
  bot_signals: BotDetectionSignals | null;

  // Extensions
  ja4_fingerprint?: string;
  ja4h_fingerprint?: string;
  ja4ssh_fingerprint?: string;
  metadata?: Record<string, any>;
}

export interface HoneypotSession {
  session_id: string;
  honeypot_id: string;
  protocol: HoneypotProtocol;
  source_ip: string;
  source_port: number;
  started_at: string;
  ended_at: string | null;
  duration_seconds: number | null;
  events_count: number;
  auth_attempts: number;
  auth_success: boolean;
  username: string | null;
  commands: string[];
  paths_accessed: string[];
  primary_category: AttackCategory;
  max_severity: AttackSeverity;
  geo: GeoLocation | null;
  ai_summary: string | null;
  matched_cves: string[];
}

export interface HoneypotAgentStatus {
  agent_id: string;
  protocol: HoneypotProtocol;
  status: 'running' | 'idle' | 'error';
  current_sessions: number;
  total_events: number;
  last_event: string | null;
  error_message: string | null;
}

export interface HoneypotStatus {
  is_running: boolean;
  ssh_enabled: boolean;
  http_enabled: boolean;
  ssh_port: number | null;
  http_port: number | null;
  active_sessions: number;
  total_events_today: number;
  total_events_all_time: number;
  unique_ips_today: number;
  last_attack: string | null;
  agents: HoneypotAgentStatus[];
}

export interface HoneypotStats {
  total_connections: number;
  total_sessions: number;
  active_sessions: number;
  total_events: number;
  unique_ips: number;
  banned_ips: number;
  top_attacker_ips: Array<{ ip: string; count: number; country_code?: string }>;
  protocol_breakdown: Record<string, number>;
  severity_breakdown: Record<string, number>;
  bot_breakdown: Record<string, number>;
  category_breakdown: Record<string, number>;
  cve_correlations: number;
  top_matched_cves: Array<{ cve_id: string; count: number }>;
  events_last_hour: number;
  events_today: number;
  events_this_week: number;
  activity_history?: Array<{ time: string; count: number }>;
}

export interface EventListResponse {
  items: AttackEvent[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

export interface SessionListResponse {
  items: HoneypotSession[];
  total: number;
  active: number;
}

export interface CVECorrelation {
  correlation_id: string;
  event_id: string;
  cve_id: string;
  cwe_ids: string[];
  confidence: number;
  match_reason: string;
  attack_pattern: string;
  timestamp: string;
}

export interface DiscoveryLog {
  timestamp: string;
  message: string;
  is_alert: boolean;
  is_error: boolean;
  agent_type?: string;
  severity?: string;
  country_code?: string;
  source_ip?: string;
}

export interface HoneypotInfo {
  id: string;
  name: string;
  description: string;
  protocol: HoneypotProtocol;
  port: number;
  enabled: boolean;
  active_attackers: number;
  total_events: number;
  tags: string[];
}

export interface HoneypotAttacker {
  ip: string;
  event_count: number;
  country_code: string | null;
  country: string | null;
  city: string | null;
  protocols: string[];
  max_severity: string;
  first_seen: string;
  last_seen: string;
  is_bot: boolean;
}

export interface HoneypotAttackersResponse {
  honeypot_id: string;
  attackers: HoneypotAttacker[];
  total: number;
}

// CVE Related Types
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
