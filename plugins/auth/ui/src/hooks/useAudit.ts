/**
 * Audit Log Hook
 *
 * Manages audit log data fetching.
 */

import { useState, useEffect, useCallback } from 'react';
import type { AuditEntry } from '../types';
import * as api from '../api/audit';

interface UseAuditOptions {
  page?: number;
  limit?: number;
  action?: string;
}

interface UseAuditReturn {
  entries: AuditEntry[];
  total: number;
  page: number;
  limit: number;
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  setPage: (page: number) => void;
  setActionFilter: (action: string | null) => void;
}

export function useAudit(options: UseAuditOptions = {}): UseAuditReturn {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(options.page || 1);
  const [limit] = useState(options.limit || 50);
  const [actionFilter, setActionFilter] = useState<string | undefined>(options.action);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await api.getAuditLog(page, limit, actionFilter);
      setEntries(response.entries);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load audit log');
    } finally {
      setIsLoading(false);
    }
  }, [page, limit, actionFilter]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleSetActionFilter = useCallback((action: string | null) => {
    setActionFilter(action || undefined);
    setPage(1);
  }, []);

  return {
    entries,
    total,
    page,
    limit,
    isLoading,
    error,
    refresh,
    setPage,
    setActionFilter: handleSetActionFilter,
  };
}
