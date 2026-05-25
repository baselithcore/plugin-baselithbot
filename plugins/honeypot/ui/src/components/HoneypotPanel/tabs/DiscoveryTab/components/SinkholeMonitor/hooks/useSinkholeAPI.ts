/**
 * useSinkholeAPI - React hook for sinkhole API operations
 */

import { useState, useCallback } from 'react';

interface SinkholeDomain {
  id: number;
  domain: string;
  anomaly_id?: string;
  detection_method: string;
  entropy?: number;
  confidence: number;
  status: 'active' | 'paused' | 'terminated';
  redirect_target?: string;
  request_count: number;
  unique_ips_count: number;
  unique_ips: string[];
  first_seen?: string;
  last_activity?: string;
  associated_cluster_id?: string;
  tags: string[];
  notes?: string;
  created_at?: string;
  activated_at?: string;
  updated_at?: string;
}

interface SinkholeStats {
  total_domains: number;
  active: number;
  paused: number;
  terminated: number;
  total_requests: number;
}

const API_BASE = '/api/honeypot/sinkhole';

export function useSinkholeAPI() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleError = useCallback((err: any) => {
    const message = err.response?.data?.detail || err.message || 'Unknown error';
    setError(message);
    console.error('Sinkhole API error:', err);
    return null;
  }, []);

  const listSinkholes = useCallback(
    async (params?: {
      status?: string;
      cluster_id?: string;
      limit?: number;
      offset?: number;
    }): Promise<SinkholeDomain[] | null> => {
      setLoading(true);
      setError(null);

      try {
        const queryParams = new URLSearchParams();
        if (params?.status) queryParams.append('status', params.status);
        if (params?.cluster_id) queryParams.append('cluster_id', params.cluster_id);
        if (params?.limit) queryParams.append('limit', params.limit.toString());
        if (params?.offset) queryParams.append('offset', params.offset.toString());

        const url = `${API_BASE}/domains${queryParams.toString() ? `?${queryParams.toString()}` : ''}`;
        const response = await fetch(url, {
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const data = await response.json();
        return data;
      } catch (err) {
        return handleError(err);
      } finally {
        setLoading(false);
      }
    },
    [handleError]
  );

  const getSinkholeStats = useCallback(async (): Promise<SinkholeStats | null> => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE}/stats`, {
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json();
    } catch (err) {
      return handleError(err);
    } finally {
      setLoading(false);
    }
  }, [handleError]);

  const createSinkhole = useCallback(
    async (data: {
      domain: string;
      anomaly_id?: string;
      detection_method?: string;
      entropy?: number;
      confidence: number;
      redirect_target?: string;
      associated_cluster_id?: string;
      tags?: string[];
      notes?: string;
    }): Promise<SinkholeDomain | null> => {
      setLoading(true);
      setError(null);

      try {
        const response = await fetch(`${API_BASE}/domains`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({
            ...data,
            detection_method: data.detection_method || 'dga',
            tags: data.tags || [],
          }),
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
      } catch (err) {
        return handleError(err);
      } finally {
        setLoading(false);
      }
    },
    [handleError]
  );

  const updateSinkholeStatus = useCallback(
    async (
      domainId: number,
      status: 'active' | 'paused' | 'terminated'
    ): Promise<SinkholeDomain | null> => {
      setLoading(true);
      setError(null);

      try {
        const response = await fetch(`${API_BASE}/domains/${domainId}/status`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ status }),
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
      } catch (err) {
        return handleError(err);
      } finally {
        setLoading(false);
      }
    },
    [handleError]
  );

  const deleteSinkhole = useCallback(
    async (domainId: number): Promise<boolean> => {
      setLoading(true);
      setError(null);

      try {
        const response = await fetch(`${API_BASE}/domains/${domainId}`, {
          method: 'DELETE',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return true;
      } catch (err) {
        handleError(err);
        return false;
      } finally {
        setLoading(false);
      }
    },
    [handleError]
  );

  const bulkActivate = useCallback(
    async (domainIds: number[]): Promise<{ activated: number; failed: number } | null> => {
      setLoading(true);
      setError(null);

      try {
        const queryParams = domainIds.map((id) => `domain_ids=${id}`).join('&');
        const response = await fetch(`${API_BASE}/domains/bulk/activate?${queryParams}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
      } catch (err) {
        return handleError(err);
      } finally {
        setLoading(false);
      }
    },
    [handleError]
  );

  const bulkPause = useCallback(
    async (domainIds: number[]): Promise<{ paused: number; failed: number } | null> => {
      setLoading(true);
      setError(null);

      try {
        const queryParams = domainIds.map((id) => `domain_ids=${id}`).join('&');
        const response = await fetch(`${API_BASE}/domains/bulk/pause?${queryParams}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
        });

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        return await response.json();
      } catch (err) {
        return handleError(err);
      } finally {
        setLoading(false);
      }
    },
    [handleError]
  );

  return {
    loading,
    error,
    listSinkholes,
    getSinkholeStats,
    createSinkhole,
    updateSinkholeStatus,
    deleteSinkhole,
    bulkActivate,
    bulkPause,
  };
}
