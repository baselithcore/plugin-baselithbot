/**
 * Discovery and threat intelligence types
 */

export interface BotnetCluster {
  cluster_id: string;
  member_ips: string[];
  suspected_cc_ip: string | null;
  associated_cc_ips?: string[];
  associated_cc_metadata?: Record<string, { connection_count: number; confidence: number }>;
  size: number;
  attack_coordination_score: number;
  common_protocols: string[];
  common_targets: string[] | null;
  detection_confidence: number;
  first_detected: string;
  last_activity: string;
  severity: string;
  modularity_score: number;
}

export interface HubNode {
  ip: string;
  degree_centrality: number;
  betweenness_centrality: number;
  connected_bots: number;
  is_confirmed_cc: boolean;
  threat_score: number;
  cluster_id: string | null;
  country_code: string | null;
  country: string | null;
  protocols: string[];
  first_seen: string;
  last_seen: string;
}

export interface NetworkAnomaly {
  anomaly_id: string;
  anomaly_type: string;
  involved_ips: string[];
  description: string;
  severity: string;
  confidence: number;
  detected_at: string;
  metadata: Record<string, any>;
  details?: Record<string, any>;
}

export interface DiscoveryGraphNode {
  id: string;
  type: string;
  cluster_id: string | null;
  degree: number;
  centrality: number;
  country_code: string | null;
  country: string | null;
  protocols: string[];
  severity: string;
  attack_count: number;
  is_hub: boolean;
  is_confirmed_cc: boolean;

  // Extended Metadata
  ja4_fingerprint?: string;
  threat_score?: number;
  community_id?: number;
}

export interface DiscoveryGraphEdge {
  source: string;
  target: string;
  weight: number;
  is_intra_cluster: boolean;
}

export interface DiscoveryGraphData {
  nodes: DiscoveryGraphNode[];
  edges: DiscoveryGraphEdge[];
  clusters: Array<{ id: string; size: number }>;
}

export interface DiscoverySummary {
  status: string;
  analysis_id?: string;
  analyzed_at?: string;
  honeypot_id?: string | null;
  total_attackers?: number;
  total_connections?: number;
  detected_botnets?: number;
  total_botnet_members?: number;
  potential_cc_servers?: number;
  hub_nodes?: number;
  anomalies_detected?: number;
  modularity_score?: number;
  high_severity_clusters?: number;
  zeroday_detection?: {
    zeroday_candidates: number;
    [key: string]: any;
  };
  exploit_patterns?: {
    patterns_detected: number;
    mitre_techniques: string[];
    [key: string]: any;
  };
  threat_intel?: {
    ioc_count: {
      ips: number;
      domains: number;
      hashes: number;
    };
    yara_rules_generated: number;
    [key: string]: any;
  };
  feature_meta?: {
    top_ja4_fingerprints: Array<{ fingerprint: string; count: number }>;
    total_ips: number;
    ssdeep_available: boolean;
    [key: string]: any;
  };
}

export type SuggestionType =
  | 'zeroday_pattern'
  | 'behavioral_cluster'
  | 'protocol_anomaly'
  | 'exploit_technique'
  | 'command_pattern';

export type SuggestionPriority = 'critical' | 'high' | 'medium' | 'low';

export interface HoneypotSuggestion {
  id: string;
  suggestion_type: SuggestionType;
  confidence: number;
  priority: SuggestionPriority;
  title: string;
  description: string;
  rationale: string;
  suggested_protocol: 'http' | 'ssh' | 'tcp';
  suggested_port: number;
  suggested_config: Record<string, any>;
  detection_patterns: Array<{
    name: string;
    regex: string;
    severity: string;
    category: string;
  }>;
  tags: string[];
  source_anomaly_ids: string[];
  source_patterns: string[];
  source_ips: string[];
  estimated_catch_rate: number;
  occurrence_count: number;
  created_at: string;
  dismissed: boolean;
  applied: boolean;
  applied_honeypot_id?: string | null;
}

export interface DiscoveryResult {
  analysis_id: string;
  honeypot_id: string | null;
  analyzed_at: string;
  total_nodes: number;
  total_edges: number;
  botnets: BotnetCluster[];
  hub_nodes: HubNode[];
  anomalies: NetworkAnomaly[];
  graph_data: DiscoveryGraphData | null;
  summary: DiscoverySummary;
  suggestions?: HoneypotSuggestion[];
}
