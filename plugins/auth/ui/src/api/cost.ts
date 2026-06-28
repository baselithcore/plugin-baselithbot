/**
 * LLM cost governance API client (admin).
 *
 * Org-wide policy (default monthly cap + warn threshold + enforcement), per-user
 * and per-group cap overrides, per-user usage overview, and usage reset.
 */

import { fetchWithAuth, handleResponse } from './client';

const API_BASE = '/api/admin/cost';

export interface CostPolicy {
  monthly_cap_usd: number | null;
  warn_threshold_pct: number;
  enforce: boolean;
}

export type UsageStatus = 'ok' | 'warning' | 'blocked';

export interface UserUsageRow {
  user_id: string;
  email: string | null;
  username: string | null;
  spend_usd: number;
  request_count: number;
  cap_usd: number | null;
  user_cap_usd: number | null;
  percent_used: number | null;
  status: UsageStatus;
}

export interface AdminUsage {
  period: string;
  currency: string;
  warn_threshold_pct: number;
  rows: UserUsageRow[];
}

export async function getCostPolicy(): Promise<CostPolicy> {
  return handleResponse<CostPolicy>(await fetchWithAuth(`${API_BASE}/policy`));
}

export async function setCostPolicy(policy: CostPolicy): Promise<CostPolicy> {
  const res = await fetchWithAuth(`${API_BASE}/policy`, {
    method: 'PUT',
    body: JSON.stringify(policy),
  });
  return handleResponse<CostPolicy>(res);
}

export async function getUsageOverview(): Promise<AdminUsage> {
  return handleResponse<AdminUsage>(await fetchWithAuth(`${API_BASE}/usage`));
}

export async function setUserCap(userId: string, capUsd: number | null): Promise<void> {
  const res = await fetchWithAuth(`${API_BASE}/users/${userId}/cap`, {
    method: 'PATCH',
    body: JSON.stringify({ monthly_cap_usd: capUsd }),
  });
  await handleResponse(res);
}

export async function setGroupCap(groupId: string, capUsd: number | null): Promise<void> {
  const res = await fetchWithAuth(`${API_BASE}/groups/${groupId}/cap`, {
    method: 'PATCH',
    body: JSON.stringify({ monthly_cap_usd: capUsd }),
  });
  await handleResponse(res);
}

export async function resetUserUsage(userId: string): Promise<void> {
  const res = await fetchWithAuth(`${API_BASE}/users/${userId}/reset`, { method: 'POST' });
  await handleResponse(res);
}
