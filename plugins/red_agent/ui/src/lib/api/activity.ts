import { call } from './client';
import type { ActivityEvent } from './types';

export const activityApi = {
  governanceStats: (opts: { sinceHours?: number; engagementId?: string } = {}) => {
    const usp = new URLSearchParams();
    usp.set('since_hours', String(opts.sinceHours ?? 24));
    if (opts.engagementId) usp.set('engagement_id', opts.engagementId);
    return call<{
      window_hours: number;
      counts: Record<string, number>;
      totals: {
        violations: number;
        adjustments: number;
        hitl_timeouts: number;
      };
    }>(`/red-agent/activity/governance-stats?${usp.toString()}`);
  },
  governanceTrend: (
    opts: {
      sinceHours?: number;
      bucket?: 'minute' | 'hour' | 'day';
      engagementId?: string;
    } = {}
  ) => {
    const usp = new URLSearchParams();
    usp.set('since_hours', String(opts.sinceHours ?? 24));
    usp.set('bucket', opts.bucket ?? 'hour');
    if (opts.engagementId) usp.set('engagement_id', opts.engagementId);
    return call<{
      window_hours: number;
      bucket: string;
      series: {
        ts: string;
        violations: number;
        adjustments: number;
        hitl_timeouts: number;
      }[];
    }>(`/red-agent/activity/governance-trend?${usp.toString()}`);
  },
  listActivity: (
    opts: {
      cockpit?: boolean;
      eventPrefix?: string[];
      limit?: number;
      engagementId?: string;
    } = {}
  ) => {
    const usp = new URLSearchParams();
    if (opts.cockpit) usp.set('cockpit', 'true');
    if (opts.limit) usp.set('limit', String(opts.limit));
    if (opts.engagementId) usp.set('engagement_id', opts.engagementId);
    for (const p of opts.eventPrefix ?? []) usp.append('event_prefix', p);
    const q = usp.toString();
    return call<ActivityEvent[]>(`/red-agent/activity${q ? `?${q}` : ''}`);
  },
};
