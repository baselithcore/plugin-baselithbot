/**
 * CVE Hunter API Client
 * API functions for CVE Hunter dashboard
 */

import type { CVERecord, SwarmStatus, CVEStats, CVEListResponse, AlertListResponse } from './types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';
const API_KEY = import.meta.env.VITE_API_KEY || '';

/**
 * Get auth headers dynamically (token may change during session)
 */
function getAuthHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};

  // Bearer token from auth system (primary)
  const token = sessionStorage.getItem('auth_access_token');
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  // Legacy API key support (secondary)
  if (API_KEY) {
    headers['X-API-Key'] = API_KEY;
  }

  return headers;
}

/**
 * Attempt to refresh the access token
 */
async function tryRefreshToken(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/api/auth/refresh`, {
      method: 'POST',
      credentials: 'include',
    });

    if (!response.ok) {
      return false;
    }

    const data = await response.json();
    if (data.access_token) {
      sessionStorage.setItem('auth_access_token', data.access_token);
      const expiry = Date.now() + (data.expires_in || 900) * 1000;
      sessionStorage.setItem('auth_token_expiry', expiry.toString());
      return true;
    }
    return false;
  } catch {
    return false;
  }
}

async function cveApiFetch<T>(path: string, init?: RequestInit, isRetry = false): Promise<T> {
  const response = await fetch(`${API_BASE}/api/cve_hunter${path}`, {
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
      ...(init?.headers || {}),
    },
    ...init,
  });

  // Handle 401 - try refresh once, then redirect
  if (response.status === 401 && !isRetry) {
    const refreshed = await tryRefreshToken();
    if (refreshed) {
      // Retry with new token
      return cveApiFetch<T>(path, init, true);
    }
    // Refresh failed, dispatch unauthorized event
    window.dispatchEvent(new CustomEvent('auth:unauthorized'));
    throw new Error('Authentication required');
  }

  // Handle 403 - forbidden (no retry)
  if (response.status === 403) {
    throw new Error('Access denied - insufficient permissions');
  }

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || 'CVE Hunter API request failed');
  }
  return (await response.json()) as T;
}

export async function fetchSwarmStatus(): Promise<SwarmStatus> {
  return cveApiFetch<SwarmStatus>('/status');
}

export async function fetchCVEs(
  page: number = 1,
  pageSize: number = 20,
  severity?: string
): Promise<CVEListResponse> {
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString(),
  });
  if (severity) params.set('severity', severity);
  return cveApiFetch<CVEListResponse>(`/cves?${params.toString()}`);
}

export async function fetchCVEDetail(cveId: string): Promise<CVERecord> {
  return cveApiFetch<CVERecord>(`/cves/${encodeURIComponent(cveId)}`);
}

export async function fetchAlerts(
  includeAcknowledged: boolean = false
): Promise<AlertListResponse> {
  const params = new URLSearchParams({
    include_acknowledged: includeAcknowledged.toString(),
  });
  return cveApiFetch<AlertListResponse>(`/alerts?${params.toString()}`);
}

export async function triggerScan(daysBack: number = 7): Promise<{
  scan_id: string;
  cves_found: number;
  new_cves: number;
  success: boolean;
}> {
  return cveApiFetch(`/scan?days_back=${daysBack}`, { method: 'POST' });
}

export async function fetchStats(): Promise<CVEStats> {
  return cveApiFetch<CVEStats>('/stats');
}

export async function acknowledgeAlert(alertId: string): Promise<{ status: string }> {
  return cveApiFetch(`/alerts/${alertId}/acknowledge`, { method: 'POST' });
}

export async function fetchDiscoveryLogs(): Promise<
  Array<{ timestamp: string; message: string; is_alert: boolean; is_error: boolean }>
> {
  return cveApiFetch<
    Array<{ timestamp: string; message: string; is_alert: boolean; is_error: boolean }>
  >('/discovery/logs');
}

export async function fetchDiscoveryFindings(): Promise<Array<any>> {
  return cveApiFetch<Array<any>>('/discovery/findings');
}

export interface AttackChain {
  chain_id: string;
  name: string;
  stages: { stage: number; cve_id: string; cwe: string[] }[];
  total_severity: number;
  description: string;
  mitre_techniques: string[];
  cve_ids: string[];
  ai_analysis?: string;
  error?: string;
}

export interface CVECorrelation {
  correlation_id: string;
  cve_ids: string[];
  correlation_type: string;
  confidence: number;
  description: string;
  severity: string;
  feedback?: string | null;
}

export interface UnifiedFinding {
  finding_id: string;
  source_type: string;
  engine: string | null;
  location: string;
  pattern: string;
  cwe_ids: string[];
  severity: string;
  confidence: number;
  score: number;
  context: string | null;
  rule_id: string | null;
  feedback?: string | null;
}

export interface DastFinding {
  finding_id: string;
  url: string;
  pattern: string;
  confidence: number;
  severity: string;
  context: string | null;
  source: string;
  engine: string | null;
  rule_id: string | null;
  feedback?: string | null;
}

export interface FindingCorrelation {
  correlation_id: string;
  correlation_type: string;
  cve_id: string;
  cwe_id: string;
  finding_ids: string[];
  confidence: number;
  description: string;
  feedback?: string | null;
}

export interface AttackChainCandidate {
  chain_id: string;
  name: string;
  matched_stages: Array<{
    stage: number;
    cwe_ids: string[];
    finding_ids: string[];
  }>;
  confidence: number;
  description: string;
  mitre_techniques: string[];
  feedback?: string | null;
}

export interface FindingCorrelationResponse {
  summary: {
    total_findings: number;
    cve_correlations: number;
    attack_chain_candidates: number;
  };
  cve_correlations: FindingCorrelation[];
  attack_chain_candidates: AttackChainCandidate[];
}

export interface FeedbackAuditItem {
  type: string;
  id: string;
  outcome: string;
  timestamp: string;
  label?: string;
  detail?: string;
}

export async function fetchAttackChains(): Promise<AttackChain[]> {
  return cveApiFetch<AttackChain[]>('/attack-chains');
}

export async function fetchCorrelations(): Promise<CVECorrelation[]> {
  return cveApiFetch<CVECorrelation[]>('/correlations');
}

export async function recordClassicCorrelationFeedback(
  correlationId: string,
  outcome: 'confirmed' | 'false_positive',
  source: string = 'user'
): Promise<{ status: string }> {
  const params = new URLSearchParams({ outcome, source });
  return cveApiFetch(`/correlations/${encodeURIComponent(correlationId)}/feedback?${params}`, {
    method: 'POST',
  });
}

export async function fetchUnifiedFindings(): Promise<UnifiedFinding[]> {
  return cveApiFetch<UnifiedFinding[]>('/findings/unified');
}

export async function fetchFindingCorrelations(): Promise<FindingCorrelationResponse> {
  return cveApiFetch<FindingCorrelationResponse>('/findings/correlations');
}

export async function fetchFeedbackAudit(limit: number = 50): Promise<FeedbackAuditItem[]> {
  return cveApiFetch<FeedbackAuditItem[]>(`/feedback/audit?limit=${limit}`);
}

export async function fetchDastFindings(): Promise<DastFinding[]> {
  return cveApiFetch<DastFinding[]>('/dast/findings');
}

export async function recordDastFeedback(
  findingId: string,
  outcome: 'confirmed' | 'false_positive',
  source: string = 'user'
): Promise<{ status: string }> {
  const params = new URLSearchParams({ outcome, source });
  return cveApiFetch(`/dast/findings/${encodeURIComponent(findingId)}/feedback?${params}`, {
    method: 'POST',
  });
}

export async function recordUnifiedFeedback(
  findingId: string,
  outcome: 'confirmed' | 'false_positive',
  source: string = 'user'
): Promise<{ status: string }> {
  const params = new URLSearchParams({ outcome, source });
  return cveApiFetch(`/findings/unified/${encodeURIComponent(findingId)}/feedback?${params}`, {
    method: 'POST',
  });
}

export async function recordCveCorrelationFeedback(
  correlationId: string,
  outcome: 'confirmed' | 'false_positive',
  source: string = 'user'
): Promise<{ status: string }> {
  const params = new URLSearchParams({ outcome, source });
  return cveApiFetch(
    `/findings/correlations/cve/${encodeURIComponent(correlationId)}/feedback?${params}`,
    { method: 'POST' }
  );
}

export async function recordAttackChainCorrelationFeedback(
  chainId: string,
  outcome: 'confirmed' | 'false_positive',
  source: string = 'user'
): Promise<{ status: string }> {
  const params = new URLSearchParams({ outcome, source });
  return cveApiFetch(
    `/findings/correlations/chain/${encodeURIComponent(chainId)}/feedback?${params}`,
    { method: 'POST' }
  );
}

export async function fetchAIAnalysis(): Promise<{ report: string }> {
  return cveApiFetch<{ report: string }>('/analyze', { method: 'POST' });
}

export async function analyzeCVE(cveId: string): Promise<CVERecord> {
  return cveApiFetch<CVERecord>(`/cves/${cveId}/analyze`, { method: 'POST' });
}

export async function analyzeAttackChain(chainId: string): Promise<AttackChain> {
  return cveApiFetch<AttackChain>(`/attack-chains/${chainId}/analyze`, { method: 'POST' });
}
