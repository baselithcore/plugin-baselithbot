export type ModalTab = 'overview' | 'technical' | 'network' | 'timeline';

// RDNS (Reverse DNS) Types
export interface RDNSResult {
  ip: string;
  hostname: string | null;
  importance: 'high' | 'medium' | 'low' | 'none';
  category: 'crawler' | 'vpn_proxy' | 'hosting' | 'isp' | 'malicious' | 'unknown' | null;
  asn: string | null;
  org: string | null;
  resolved_at: string | null;
  cached: boolean;
  error: string | null;
}

export interface RDNSEnrichmentResponse {
  results: RDNSResult[];
  total: number;
  resolved_count: number;
  cached_count: number;
  processing_time_ms: number;
}
