/**
 * Sessions Hook
 *
 * Manages session data fetching.
 */

import { useState, useEffect, useCallback } from 'react';
import type { Session } from '../types';
import * as api from '../api/sessions';

interface UseSessionsReturn {
  sessions: Session[];
  total: number;
  isLoading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
  filterByUser: (userId: string | null) => void;
}

export function useSessions(userId?: string): UseSessionsReturn {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [total, setTotal] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [userFilter, setUserFilter] = useState<string | undefined>(userId);

  const refresh = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await api.listSessions(userFilter);
      setSessions(response.sessions);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load sessions');
    } finally {
      setIsLoading(false);
    }
  }, [userFilter]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const filterByUser = useCallback((id: string | null) => {
    setUserFilter(id || undefined);
  }, []);

  return {
    sessions,
    total,
    isLoading,
    error,
    refresh,
    filterByUser,
  };
}
