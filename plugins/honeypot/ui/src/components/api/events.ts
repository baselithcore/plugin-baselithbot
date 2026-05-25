/**
 * Events & Sessions APIs
 * Attack events, sessions, logs, analysis, and attacker tracking
 */

import { honeypotApiFetch } from './core';
import type {
  EventListResponse,
  SessionListResponse,
  AttackEvent,
  HoneypotSession,
  CVECorrelation,
  DiscoveryLog,
  HoneypotAttacker,
} from '../types';

export async function fetchEvents(
  page: number = 1,
  pageSize: number = 20,
  filters?: {
    protocol?: string;
    severity?: string;
    category?: string;
    source_ip?: string;
    honeypot_id?: string;
    country?: string;
    is_bot?: boolean;
  }
): Promise<EventListResponse> {
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString(),
  });
  if (filters?.protocol) params.set('protocol', filters.protocol);
  if (filters?.severity) params.set('severity', filters.severity);
  if (filters?.category) params.set('category', filters.category);
  if (filters?.source_ip) params.set('source_ip', filters.source_ip);
  if (filters?.honeypot_id) params.set('honeypot_id', filters.honeypot_id);
  if (filters?.country) params.set('country', filters.country);
  if (filters?.is_bot !== undefined) params.set('is_bot', String(filters.is_bot));

  return honeypotApiFetch<EventListResponse>(`/events?${params.toString()}`);
}

export async function fetchEventDetail(eventId: string): Promise<AttackEvent> {
  return honeypotApiFetch<AttackEvent>(`/events/${encodeURIComponent(eventId)}`);
}

export async function fetchSessions(
  page: number = 1,
  pageSize: number = 20,
  filters?: {
    protocol?: string;
    active_only?: boolean;
  }
): Promise<SessionListResponse> {
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString(),
  });
  if (filters?.protocol) params.set('protocol', filters.protocol);
  if (filters?.active_only) params.set('active_only', 'true');

  return honeypotApiFetch<SessionListResponse>(`/sessions?${params.toString()}`);
}

export async function fetchSessionDetail(sessionId: string): Promise<HoneypotSession> {
  return honeypotApiFetch<HoneypotSession>(`/sessions/${encodeURIComponent(sessionId)}`);
}

export async function fetchLogs(limit: number = 100): Promise<DiscoveryLog[]> {
  return honeypotApiFetch<DiscoveryLog[]>(`/logs?limit=${limit}`);
}

export async function analyzeEvent(eventId: string): Promise<{
  event_id: string;
  analysis: string;
  recommendations: string[];
}> {
  return honeypotApiFetch(`/events/${encodeURIComponent(eventId)}/analyze`, {
    method: 'POST',
  });
}

export async function analyzeSession(sessionId: string): Promise<{
  session_id: string;
  analysis: string;
  threat_level: string;
  commands_analyzed: number;
}> {
  return honeypotApiFetch(`/sessions/${encodeURIComponent(sessionId)}/analyze`, {
    method: 'POST',
  });
}

export async function fetchCVECorrelations(limit: number = 50): Promise<{
  items: CVECorrelation[];
  total: number;
  unique_cves: number;
}> {
  return honeypotApiFetch(`/cve-correlations?limit=${limit}`);
}

export async function fetchTopAttackers(
  limit: number = 10
): Promise<Array<{ ip: string; count: number }>> {
  return honeypotApiFetch(`/top-attackers?limit=${limit}`);
}

/**
 * Fetch all unique attackers with aggregated data.
 * Optimized for Globe visualization - returns all IPs regardless of event count.
 */
export async function fetchAllAttackers(
  honeypotId?: string,
  limit: number = 500,
  timeRange: string = '24h'
): Promise<{ attackers: HoneypotAttacker[]; total: number }> {
  const params = new URLSearchParams({ limit: limit.toString() });
  if (honeypotId) params.set('honeypot_id', honeypotId);
  // Always send time_range to override backend default
  params.set('time_range', timeRange);
  return honeypotApiFetch(`/attackers?${params.toString()}`);
}

export async function fetchAttackPatterns(): Promise<{
  by_category: Record<string, number>;
  by_severity: Record<string, number>;
  total_patterns_detected: number;
}> {
  return honeypotApiFetch('/patterns');
}
