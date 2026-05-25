/**
 * Discovery APIs (Botnet Detection)
 * Advanced threat detection, botnet analysis, and anomaly detection
 */

import { honeypotApiFetch } from './core';
import type { DiscoveryResult, DiscoverySummary } from '../types';

export async function runDiscoveryAnalysis(
  honeypotId?: string,
  options?: {
    timeWindowHours?: number;
    minClusterSize?: number;
    resolution?: number;
  }
): Promise<DiscoveryResult> {
  const params = new URLSearchParams();
  if (honeypotId) params.append('honeypot_id', honeypotId);
  if (options?.timeWindowHours) params.append('time_window_hours', String(options.timeWindowHours));
  if (options?.minClusterSize) params.append('min_cluster_size', String(options.minClusterSize));
  if (options?.resolution) params.append('resolution', String(options.resolution));

  const query = params.toString();
  return honeypotApiFetch<DiscoveryResult>(`/discovery/analyze${query ? `?${query}` : ''}`, {
    method: 'POST',
  });
}

/**
 * Fetch cached discovery result without re-running analysis.
 * Use this for fast loading on tab mount.
 */
export async function fetchDiscoveryResult(honeypotId?: string): Promise<DiscoveryResult | null> {
  const params = honeypotId ? `?honeypot_id=${encodeURIComponent(honeypotId)}` : '';
  try {
    return await honeypotApiFetch<DiscoveryResult>(`/discovery/result${params}`);
  } catch {
    // No cached result available - return null to indicate fresh analysis needed
    return null;
  }
}

export async function fetchDiscoverySummary(honeypotId?: string): Promise<DiscoverySummary> {
  const params = honeypotId ? `?honeypot_id=${encodeURIComponent(honeypotId)}` : '';
  return honeypotApiFetch<DiscoverySummary>(`/discovery/summary${params}`);
}

export async function fetchBotnets(honeypotId?: string): Promise<any[]> {
  const params = honeypotId ? `?honeypot_id=${encodeURIComponent(honeypotId)}` : '';
  return honeypotApiFetch<any[]>(`/discovery/botnets${params}`);
}

export async function fetchHubNodes(honeypotId?: string): Promise<any[]> {
  const params = honeypotId ? `?honeypot_id=${encodeURIComponent(honeypotId)}` : '';
  return honeypotApiFetch<any[]>(`/discovery/hubs${params}`);
}

export async function fetchDiscoveryGraph(honeypotId?: string): Promise<any> {
  const params = honeypotId ? `?honeypot_id=${encodeURIComponent(honeypotId)}` : '';
  return honeypotApiFetch<any>(`/discovery/graph${params}`);
}

export async function fetchAnomalies(honeypotId?: string): Promise<any[]> {
  const params = honeypotId ? `?honeypot_id=${encodeURIComponent(honeypotId)}` : '';
  return honeypotApiFetch<any[]>(`/discovery/anomalies${params}`);
}

// RDNS Types (matching backend models)
export interface RDNSResult {
  ip: string;
  hostname: string | null;
  importance: 'high' | 'medium' | 'low' | 'none';
  category: string | null;
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

/**
 * Fetch RDNS-enriched IP data with significance filtering.
 * Resolves hostnames for intercepted IPs and scores their significance.
 */
export async function fetchRDNSData(
  honeypotId?: string,
  minImportance: string = 'low',
  limit: number = 100
): Promise<RDNSEnrichmentResponse> {
  const params = new URLSearchParams();
  if (honeypotId) params.append('honeypot_id', honeypotId);
  params.append('min_importance', minImportance);
  params.append('limit', String(limit));
  return honeypotApiFetch<RDNSEnrichmentResponse>(`/discovery/rdns?${params}`);
}
