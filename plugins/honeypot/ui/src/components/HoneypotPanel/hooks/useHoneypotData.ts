/**
 * useHoneypotData - Data fetching and state management for Honeypot dashboard
 */

import { useState, useEffect, useCallback } from 'react';
import * as api from '../../api';
import type { HoneypotStatus, HoneypotStats, AttackEvent, DiscoveryLog } from '../../types';

interface UseHoneypotDataReturn {
  status: HoneypotStatus | null;
  stats: HoneypotStats | null;
  events: AttackEvent[];
  logs: DiscoveryLog[];
  isLoading: boolean;
  error: string | null;
  setStats: React.Dispatch<React.SetStateAction<HoneypotStats | null>>;
  setEvents: React.Dispatch<React.SetStateAction<AttackEvent[]>>;
  setLogs: React.Dispatch<React.SetStateAction<DiscoveryLog[]>>;
}

/**
 * Hook for fetching and managing honeypot dashboard data
 *
 * Note: Polling interval increased to 15s as backup - SSE provides real-time updates.
 */
export function useHoneypotData(
  refreshInterval = 15000,
  honeypotId: string | null = null
): UseHoneypotDataReturn {
  const [status, setStatus] = useState<HoneypotStatus | null>(null);
  const [stats, setStats] = useState<HoneypotStats | null>(null);
  const [events, setEvents] = useState<AttackEvent[]>([]);
  const [logs, setLogs] = useState<DiscoveryLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchInitialData = useCallback(async () => {
    try {
      setIsLoading(true);
      const [statusData, statsData, eventsData, logsData] = await Promise.all([
        api.fetchStatus(),
        api.fetchStats(),
        api.fetchEvents(1, 50, honeypotId ? { honeypot_id: honeypotId } : undefined),
        api.fetchLogs(100),
      ]);
      setStatus(statusData);
      setStats(statsData);
      setEvents(eventsData.items);
      setLogs(logsData);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch data');
    } finally {
      setIsLoading(false);
    }
  }, [honeypotId]);

  const pollStats = useCallback(async () => {
    try {
      // Poll status, stats, logs AND events
      const [statusData, statsData, logsData, eventsData] = await Promise.all([
        api.fetchStatus(),
        api.fetchStats(),
        api.fetchLogs(50),
        api.fetchEvents(1, 20, honeypotId ? { honeypot_id: honeypotId } : undefined),
      ]);
      setStatus(statusData);
      setStats(statsData);

      // Merge polled logs with existing logs (deduplicate via timestamp+message signature)
      setLogs((prevLogs) => {
        // Create signature set from existing logs
        const existingSignatures = new Set(
          prevLogs.map((l) => `${l.timestamp}|${l.message}|${l.source_ip || ''}`)
        );

        // Filter out polled logs that already exist
        const newUniqueLogs = logsData.filter(
          (l) => !existingSignatures.has(`${l.timestamp}|${l.message}|${l.source_ip || ''}`)
        );

        if (newUniqueLogs.length === 0) return prevLogs;

        // Combine, sort descending, and keep latest 100
        return [...newUniqueLogs, ...prevLogs]
          .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
          .slice(0, 100);
      });

      // Merge polled events with existing events (deduplicate via event_id)
      setEvents((prevEvents) => {
        const existingIds = new Set(prevEvents.map((e) => e.event_id));
        const newUniqueEvents = eventsData.items.filter((e) => !existingIds.has(e.event_id));

        if (newUniqueEvents.length === 0) return prevEvents;

        // Combine, sort descending, and keep latest 50
        return [...newUniqueEvents, ...prevEvents]
          .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
          .slice(0, 50);
      });
    } catch (err) {
      console.warn('Polling failed', err);
    }
  }, [honeypotId]);

  useEffect(() => {
    fetchInitialData();
    const interval = setInterval(pollStats, refreshInterval);
    return () => clearInterval(interval);
  }, [fetchInitialData, pollStats, refreshInterval]);

  return {
    status,
    stats,
    events,
    logs,
    isLoading,
    error,
    setStats,
    setEvents,
    setLogs,
  };
}
