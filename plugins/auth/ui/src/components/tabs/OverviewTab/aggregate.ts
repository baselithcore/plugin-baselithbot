/**
 * Pure aggregation helpers for the Overview dashboard. Kept side-effect free so
 * the data shaping is trivially testable and the view stays declarative.
 */

import type { User, AuditEntry } from '../../../types';
import type { UserUsageRow } from '../../../api/cost';

const DAY_MS = 86_400_000;

const startOfDay = (d: Date): Date => {
  const x = new Date(d);
  x.setHours(0, 0, 0, 0);
  return x;
};

export interface DaySeries {
  labels: string[];
  values: number[];
}

/** Bucket audit events into per-day counts for the last `days` days. */
export function bucketByDay(entries: AuditEntry[], days = 14): DaySeries {
  const today = startOfDay(new Date());
  const start = new Date(today.getTime() - (days - 1) * DAY_MS);
  const values = new Array<number>(days).fill(0);
  const labels: string[] = [];
  for (let i = 0; i < days; i++) {
    const d = new Date(start.getTime() + i * DAY_MS);
    labels.push(`${d.getMonth() + 1}/${d.getDate()}`);
  }
  for (const e of entries) {
    if (!e.created_at) continue;
    const idx = Math.round(
      (startOfDay(new Date(e.created_at)).getTime() - start.getTime()) / DAY_MS
    );
    if (idx >= 0 && idx < days) values[idx] += 1;
  }
  return { labels, values };
}

/** Count events whose timestamp falls on the current calendar day. */
export function eventsToday(entries: AuditEntry[]): number {
  const today = startOfDay(new Date()).getTime();
  return entries.filter(
    (e) => e.created_at && startOfDay(new Date(e.created_at)).getTime() === today
  ).length;
}

export interface RoleCount {
  role: string;
  count: number;
}

/** Distribution of accounts per role (users with no role count as `user`). */
export function roleDistribution(users: User[]): RoleCount[] {
  const m = new Map<string, number>();
  for (const u of users) {
    const roles = u.roles?.length ? u.roles : ['user'];
    for (const r of roles) m.set(r, (m.get(r) ?? 0) + 1);
  }
  return [...m.entries()]
    .map(([role, count]) => ({ role, count }))
    .sort((a, b) => b.count - a.count);
}

export interface MfaStats {
  enabled: number;
  total: number;
  pct: number;
}

export function mfaStats(users: User[]): MfaStats {
  const total = users.length;
  const enabled = users.filter((u) => u.mfa_enabled).length;
  return { enabled, total, pct: total ? Math.round((enabled / total) * 100) : 0 };
}

const PRIVILEGED_ROLES = new Set(['admin', 'superuser', 'owner']);

/** Accounts holding a privileged role — the privilege-exposure indicator. */
export function privilegedCount(users: User[]): number {
  return users.filter((u) => (u.roles ?? []).some((r) => PRIVILEGED_ROLES.has(r))).length;
}

/** Sum of outstanding failed-login attempts across accounts (brute-force signal). */
export function failedLoginTotal(users: User[]): number {
  return users.reduce((s, u) => s + (u.failed_login_attempts || 0), 0);
}

export interface UsageSummary {
  totalSpend: number;
  totalRequests: number;
  top: { label: string; value: number }[];
  currency: string;
}

/** Summarize per-user LLM spend into a total + top spenders for the bar list. */
export function usageSummary(rows: UserUsageRow[], currency: string, topN = 5): UsageSummary {
  const totalSpend = rows.reduce((s, r) => s + (r.spend_usd || 0), 0);
  const totalRequests = rows.reduce((s, r) => s + (r.request_count || 0), 0);
  const top = [...rows]
    .filter((r) => r.spend_usd > 0)
    .sort((a, b) => b.spend_usd - a.spend_usd)
    .slice(0, topN)
    .map((r) => ({
      label: r.email || r.username || r.user_id.slice(0, 8),
      value: r.spend_usd,
    }));
  return { totalSpend, totalRequests, top, currency };
}
