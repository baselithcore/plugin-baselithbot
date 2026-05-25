/**
 * Report generation types
 */

export type ReportFormat = 'pdf' | 'markdown' | 'json';
export type ReportType =
  | 'executive'
  | 'technical'
  | 'compliance'
  | 'incident'
  | 'pentest'
  | 'threat_intel'
  | 'research';
export type ReportSection =
  | 'executive_summary'
  | 'threat_landscape'
  | 'attack_analytics'
  | 'geo_analysis'
  | 'botnet_discovery'
  | 'pentest_results'
  | 'cve_correlations'
  | 'recommendations'
  | 'ioc_list'
  | 'timeline'
  // Research-specific sections
  | 'abstract'
  | 'key_findings'
  | 'mitre_mapping'
  | 'statistical_analysis'
  | 'payload_analysis';

export interface ReportConfig {
  report_type: ReportType;
  format: ReportFormat;
  sections: ReportSection[];
  time_range_hours: number;
  honeypot_id?: string | null;
  include_raw_data?: boolean;
  organization_name?: string | null;
  classification?: string;
}

export interface ThreatSummary {
  total_events: number;
  unique_attackers: number;
  critical_events: number;
  high_events: number;
  medium_events: number;
  low_events: number;
  top_attack_categories: Record<string, number>;
  top_attacking_countries: Record<string, number>;
  top_protocols: Record<string, number>;
  detected_botnets: number;
  potential_cc_servers: number;
  cve_matches: number;
  bot_traffic_percentage: number;
}

export interface AttackTimelineEntry {
  timestamp: string;
  event_type: string;
  source_ip: string;
  severity: string;
  category: string;
  description: string;
  country_code?: string | null;
}

export interface VulnerabilityItem {
  finding_id: string;
  name: string;
  severity: string;
  category: string;
  description: string;
  remediation: string;
  cve_references: string[];
  confidence: number;
}

export interface IOCEntry {
  ioc_type: string;
  value: string;
  first_seen: string;
  last_seen: string;
  confidence: number;
  associated_campaigns: string[];
  threat_level: string;
}

export interface GeoDistribution {
  country_code: string;
  country_name: string;
  attack_count: number;
  unique_ips: number;
  primary_attack_types: string[];
}

export interface BotnetSummaryReport {
  cluster_id: string;
  member_count: number;
  severity: string;
  attack_coordination_score: number;
  suspected_cc_servers: string[];
  common_protocols: string[];
  first_detected: string;
  last_activity: string;
}

export interface PentestSummaryItem {
  pentest_id: string;
  playbook_name: string;
  security_score: number;
  total_tests: number;
  passed_tests: number;
  failed_tests: number;
  critical_findings: number;
  high_findings: number;
  status: string;
  completed_at?: string | null;
}

export interface ReportMetadata {
  report_id: string;
  generated_at: string;
  generated_by: string;
  report_type: ReportType;
  classification: string;
  time_range_start: string;
  time_range_end: string;
  honeypot_filter?: string | null;
  organization?: string | null;
  version: string;
}

export interface SecurityReport {
  metadata: ReportMetadata;
  threat_summary: ThreatSummary;
  executive_summary?: string | null;
  attack_timeline: AttackTimelineEntry[];
  geo_distribution: GeoDistribution[];
  botnet_activity: BotnetSummaryReport[];
  vulnerabilities: VulnerabilityItem[];
  pentest_results: PentestSummaryItem[];
  iocs: IOCEntry[];
  recommendations: string[];
  raw_data?: Record<string, unknown> | null;
}

export interface ReportGenerationRequest {
  config: ReportConfig;
  title?: string | null;
}

export interface ReportTypeInfo {
  id: ReportType;
  name: string;
  description: string;
}

export interface ReportSectionInfo {
  id: ReportSection;
  name: string;
  description: string;
}

export interface ReportTypesResponse {
  types: ReportTypeInfo[];
  sections: ReportSectionInfo[];
  formats: { id: ReportFormat; name: string }[];
}
