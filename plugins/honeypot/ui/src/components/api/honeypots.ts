/**
 * Honeypot Registry & Management APIs
 * Registry operations, status, stats, and honeypot control
 */

import { honeypotApiFetch } from './core';
import type {
  HoneypotStatus,
  HoneypotStats,
  HoneypotInfo,
  HoneypotAttackersResponse,
  EventListResponse,
} from '../types';

export async function fetchStatus(): Promise<HoneypotStatus> {
  return honeypotApiFetch<HoneypotStatus>('/status');
}

export async function fetchStats(honeypotId?: string): Promise<HoneypotStats> {
  const query = honeypotId ? `?honeypot_id=${encodeURIComponent(honeypotId)}` : '';
  return honeypotApiFetch<HoneypotStats>(`/stats${query}`);
}

export async function startHoneypot(): Promise<{ status: string; message: string }> {
  return honeypotApiFetch('/start', { method: 'POST' });
}

export async function stopHoneypot(): Promise<{ status: string; message: string }> {
  return honeypotApiFetch('/stop', { method: 'POST' });
}

export async function fetchHoneypots(): Promise<HoneypotInfo[]> {
  return honeypotApiFetch<HoneypotInfo[]>('/honeypots');
}

export async function fetchHoneypot(honeypotId: string): Promise<HoneypotInfo> {
  return honeypotApiFetch<HoneypotInfo>(`/honeypots/${encodeURIComponent(honeypotId)}`);
}

export async function fetchHoneypotEvents(
  honeypotId: string,
  page: number = 1,
  pageSize: number = 50,
  filters?: {
    protocol?: string;
    severity?: string;
    category?: string;
    source_ip?: string;
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

  return honeypotApiFetch<EventListResponse>(
    `/honeypots/${encodeURIComponent(honeypotId)}/events?${params.toString()}`
  );
}

export async function fetchHoneypotAttackers(
  honeypotId: string
): Promise<HoneypotAttackersResponse> {
  return honeypotApiFetch<HoneypotAttackersResponse>(
    `/honeypots/${encodeURIComponent(honeypotId)}/attackers`
  );
}
