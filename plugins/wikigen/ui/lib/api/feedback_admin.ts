/**
 * Feedback admin API client.
 *
 * Endpoint montati a ``/api/admin/feedback/*``. Gating server-side:
 * - ``feedback.read``    → list/stats/detail/export/meta/sources
 * - ``feedback.triage``  → PATCH triage (mig 018)
 * - ``feedback.delete``  → DELETE moderazione
 */

import { authFetch, json } from './client';

export type FeedbackStatus = 'open' | 'triaged' | 'resolved' | 'dismissed';

export interface FeedbackSource {
  document_id?: string;
  title?: string;
  score?: number;
  [k: string]: unknown;
}

export interface FeedbackItem {
  id: string;
  tenant_id: string;
  user_id: string | null;
  user_email: string | null;
  message_id: string | null;
  conversation_id: string | null;
  rating: 'up' | 'down';
  reason: string | null;
  question: string | null;
  answer: string | null;
  sources: FeedbackSource[] | null;
  created_at: string | null;
  status: FeedbackStatus;
  tags: string[];
  resolution_note: string | null;
  resolved_by_user_id: string | null;
  resolved_by_email: string | null;
  resolved_at: string | null;
}

export interface FeedbackListResponse {
  items: FeedbackItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface FeedbackTrendBucket {
  bucket: string;
  up: number;
  down: number;
}

export interface FeedbackTopQuestion {
  question: string;
  count: number;
  down: number;
}

export interface FeedbackStatusBreakdown {
  open: number;
  triaged: number;
  resolved: number;
  dismissed: number;
}

export interface FeedbackAnomaly {
  severity: 'warning' | 'high';
  down_24h: number;
  down_rate_24h: number;
  down_rate_baseline: number;
  ratio: number;
  message: string;
}

export interface FeedbackStats {
  total: number;
  up: number;
  down: number;
  positive_rate: number;
  with_reason: number;
  unique_users: number;
  trend: FeedbackTrendBucket[];
  top_questions: FeedbackTopQuestion[];
  status_breakdown: FeedbackStatusBreakdown;
  anomaly: FeedbackAnomaly | null;
}

export interface FeedbackSourceStat {
  document_id: string;
  title: string;
  total: number;
  up: number;
  down: number;
  down_rate: number;
}

export interface FeedbackMeta {
  statuses: FeedbackStatus[];
  suggested_tags: string[];
}

export interface FeedbackFilters {
  rating?: 'up' | 'down' | null;
  status?: FeedbackStatus | null;
  tag?: string | null;
  user_id?: string | null;
  message_id?: string | null;
  since?: string | null;
  until?: string | null;
  search?: string | null;
  limit?: number;
  offset?: number;
}

export interface TriagePatch {
  status?: FeedbackStatus | null;
  tags?: string[] | null;
  resolution_note?: string | null;
}

const BASE_PATH = '/admin/feedback';

function buildQuery(filters: FeedbackFilters): string {
  const params = new URLSearchParams();
  if (filters.rating) params.set('rating', filters.rating);
  if (filters.status) params.set('status', filters.status);
  if (filters.tag) params.set('tag', filters.tag);
  if (filters.user_id) params.set('user_id', filters.user_id);
  if (filters.message_id) params.set('message_id', filters.message_id);
  if (filters.since) params.set('since', filters.since);
  if (filters.until) params.set('until', filters.until);
  if (filters.search) params.set('search', filters.search);
  if (filters.limit !== undefined) params.set('limit', String(filters.limit));
  if (filters.offset !== undefined) params.set('offset', String(filters.offset));
  const q = params.toString();
  return q ? `?${q}` : '';
}

export const listFeedback = (
  filters: FeedbackFilters = {}
): Promise<FeedbackListResponse> => json(`${BASE_PATH}${buildQuery(filters)}`);

export const getFeedback = (id: string): Promise<FeedbackItem> =>
  json(`${BASE_PATH}/${encodeURIComponent(id)}`);

export const deleteFeedback = (id: string): Promise<{ status: string; id: string }> =>
  json(`${BASE_PATH}/${encodeURIComponent(id)}`, { method: 'DELETE' });

export const patchTriage = (id: string, patch: TriagePatch): Promise<FeedbackItem> =>
  json(`${BASE_PATH}/${encodeURIComponent(id)}`, {
    method: 'PATCH',
    body: JSON.stringify(patch),
  });

export const fetchMeta = (): Promise<FeedbackMeta> => json(`${BASE_PATH}/meta`);

export interface FeedbackStatsArgs {
  since?: string | null;
  until?: string | null;
  bucket?: 'hour' | 'day' | 'week';
}

export const fetchStats = (args: FeedbackStatsArgs = {}): Promise<FeedbackStats> => {
  const params = new URLSearchParams();
  if (args.since) params.set('since', args.since);
  if (args.until) params.set('until', args.until);
  if (args.bucket) params.set('bucket', args.bucket);
  const q = params.toString();
  return json(`${BASE_PATH}/stats${q ? `?${q}` : ''}`);
};

export const fetchSourceStats = (
  args: { since?: string | null; until?: string | null; limit?: number } = {}
): Promise<FeedbackSourceStat[]> => {
  const params = new URLSearchParams();
  if (args.since) params.set('since', args.since);
  if (args.until) params.set('until', args.until);
  if (args.limit) params.set('limit', String(args.limit));
  const q = params.toString();
  return json(`${BASE_PATH}/stats/sources${q ? `?${q}` : ''}`);
};

/**
 * Download CSV — bypass json() helper perché response binaria.
 */
export async function downloadCsv(filters: FeedbackFilters = {}): Promise<void> {
  const params = new URLSearchParams();
  if (filters.rating) params.set('rating', filters.rating);
  if (filters.status) params.set('status', filters.status);
  if (filters.tag) params.set('tag', filters.tag);
  if (filters.user_id) params.set('user_id', filters.user_id);
  if (filters.message_id) params.set('message_id', filters.message_id);
  if (filters.since) params.set('since', filters.since);
  if (filters.until) params.set('until', filters.until);
  if (filters.search) params.set('search', filters.search);
  params.set('limit', String(filters.limit ?? 10000));
  const url = `${BASE_PATH}/export.csv?${params.toString()}`;
  const res = await authFetch(url);
  if (!res.ok) {
    throw new Error(`export CSV fallito (${res.status})`);
  }
  const blob = await res.blob();
  const link = document.createElement('a');
  const objectUrl = URL.createObjectURL(blob);
  link.href = objectUrl;
  const cd = res.headers.get('Content-Disposition') ?? '';
  const match = /filename="([^"]+)"/.exec(cd);
  link.download = match?.[1] ?? `feedback-${Date.now()}.csv`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(objectUrl);
}
