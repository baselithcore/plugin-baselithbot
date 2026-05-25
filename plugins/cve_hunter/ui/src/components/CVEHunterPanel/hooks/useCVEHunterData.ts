/**
 * useCVEHunterData - Main data fetching hook for CVE Hunter dashboard
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  fetchSwarmStatus,
  fetchCVEs,
  fetchStats,
  fetchDiscoveryLogs,
  fetchDiscoveryFindings,
} from '../../api';
import type { CVERecord, SwarmStatus, CVEStats, CVEAgentStatus } from '../../types';
import type { DiscoveryLog, Finding } from '../types';
import { DEFAULT_AGENTS } from '../utils';

export interface UseCVEHunterDataReturn {
  // State
  swarmStatus: SwarmStatus | null;
  cves: CVERecord[];
  stats: CVEStats | null;
  discoveryLogs: DiscoveryLog[];
  findings: Finding[];
  isLoading: boolean;
  error: string | null;

  // Computed
  agents: CVEAgentStatus[];

  // Setters
  setDiscoveryLogs: React.Dispatch<React.SetStateAction<DiscoveryLog[]>>;
  setError: React.Dispatch<React.SetStateAction<string | null>>;

  // Refs
  terminalRef: React.RefObject<HTMLDivElement>;
  terminalEndRef: React.RefObject<HTMLDivElement>;

  // Actions
  loadData: () => Promise<void>;
}

/**
 * Hook for fetching and managing CVE Hunter main dashboard data
 */
export function useCVEHunterData(): UseCVEHunterDataReturn {
  const [swarmStatus, setSwarmStatus] = useState<SwarmStatus | null>(null);
  const [cves, setCVEs] = useState<CVERecord[]>([]);
  const [stats, setStats] = useState<CVEStats | null>(null);
  const [discoveryLogs, setDiscoveryLogs] = useState<DiscoveryLog[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Refs for terminal auto-scroll
  const terminalRef = useRef<HTMLDivElement>(null);
  const terminalEndRef = useRef<HTMLDivElement>(null);

  // Compute agents from swarm status or use defaults
  const agents: CVEAgentStatus[] = swarmStatus?.agents?.length
    ? swarmStatus.agents
    : DEFAULT_AGENTS;

  const loadData = useCallback(async () => {
    try {
      const [statusData, cveData, statsData] = await Promise.all([
        fetchSwarmStatus(),
        fetchCVEs(1, 100),
        fetchStats(),
      ]);
      setSwarmStatus(statusData);
      setCVEs(cveData.items);
      setStats(statsData);
      setIsLoading(false);
    } catch (err) {
      console.error('Failed to load data:', err);
      if (isLoading) {
        setError('Failed to connect to swarm coordinator.');
        setIsLoading(false);
      }
    }
  }, [isLoading]);

  const loadLogs = useCallback(async () => {
    try {
      const logs = await fetchDiscoveryLogs();
      setDiscoveryLogs(logs);
    } catch (err) {
      console.error('Failed to fetch discovery logs', err);
    }
  }, []);

  const loadFindings = useCallback(async () => {
    try {
      const newFindings = await fetchDiscoveryFindings();
      setFindings(newFindings.reverse());
    } catch (err) {
      console.error('Failed to fetch findings', err);
    }
  }, []);

  // Initial Load & Polling for Data (30s)
  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 30000);
    return () => clearInterval(interval);
  }, [loadData]);

  // Poll for Logs & Findings (2s)
  useEffect(() => {
    loadLogs();
    loadFindings();
    const interval = setInterval(() => {
      loadLogs();
      loadFindings();
    }, 2000);
    return () => clearInterval(interval);
  }, [loadLogs, loadFindings]);

  return {
    swarmStatus,
    cves,
    stats,
    discoveryLogs,
    findings,
    isLoading,
    error,
    agents,
    setDiscoveryLogs,
    setError,
    terminalRef,
    terminalEndRef,
    loadData,
  };
}
