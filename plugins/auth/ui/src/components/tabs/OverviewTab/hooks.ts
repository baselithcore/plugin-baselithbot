/**
 * Overview data hook — fans out to the existing admin endpoints and shapes the
 * results client-side (no new backend). Each call degrades independently so a
 * disabled subsystem (e.g. cost governance) never blanks the whole dashboard.
 */

import { useEffect, useState } from 'react';
import { listUsers } from '../../../api/users';
import { listSessions } from '../../../api/sessions';
import { getAuditLog } from '../../../api/audit';
import { getUsageOverview } from '../../../api/cost';
import type { User, AuditEntry } from '../../../types';
import {
  bucketByDay,
  eventsToday,
  roleDistribution,
  mfaStats,
  usageSummary,
  type DaySeries,
  type RoleCount,
  type MfaStats,
  type UsageSummary,
} from './aggregate';

export interface OverviewData {
  totalUsers: number;
  activeUsers: number;
  lockedUsers: number;
  activeSessions: number;
  mfa: MfaStats;
  roles: RoleCount[];
  activity: DaySeries;
  eventsToday: number;
  recent: AuditEntry[];
  usage: UsageSummary | null;
}

export interface UseOverview {
  data: OverviewData | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

export function useOverview(): UseOverview {
  const [data, setData] = useState<OverviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [nonce, setNonce] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    (async () => {
      const [usersRes, sessRes, auditRes, usageRes] = await Promise.all([
        listUsers(1, 200, true).catch(() => null),
        listSessions().catch(() => null),
        getAuditLog(1, 200).catch(() => null),
        getUsageOverview().catch(() => null),
      ]);
      if (cancelled) return;
      if (!usersRes && !sessRes && !auditRes) {
        setError('load_failed');
        setLoading(false);
        return;
      }
      const users: User[] = usersRes?.users ?? [];
      const entries: AuditEntry[] = auditRes?.entries ?? [];
      setData({
        totalUsers: usersRes?.total ?? users.length,
        activeUsers: users.filter((u) => u.is_active).length,
        lockedUsers: users.filter((u) => u.is_locked).length,
        activeSessions: sessRes?.total ?? 0,
        mfa: mfaStats(users),
        roles: roleDistribution(users),
        activity: bucketByDay(entries, 14),
        eventsToday: eventsToday(entries),
        recent: entries.slice(0, 6),
        usage: usageRes ? usageSummary(usageRes.rows, usageRes.currency) : null,
      });
      setLoading(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [nonce]);

  return { data, loading, error, reload: () => setNonce((n) => n + 1) };
}
