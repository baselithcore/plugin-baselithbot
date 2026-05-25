import { useState, useEffect, useCallback } from 'react';
import { GraphData } from './types';
import { API_BASE, AUTH_HEADERS } from '../../../api/client';

export const useGraphData = (centerNodeId: string, isOpen: boolean) => {
  const [data, setData] = useState<GraphData>({ nodes: [], links: [] });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    if (!centerNodeId || !isOpen) return;

    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `${API_BASE}/console/kb/graph?path=${encodeURIComponent(centerNodeId)}`,
        {
          headers: AUTH_HEADERS,
        }
      );

      const contentType = response.headers.get('content-type');
      if (!response.ok) {
        let errorMessage = 'Failed to fetch graph data';
        if (contentType?.includes('application/json')) {
          const errData = await response.json();
          errorMessage = errData.detail || errorMessage;
        } else {
          errorMessage = `Server Error: ${response.status} ${response.statusText}`;
        }
        throw new Error(errorMessage);
      }

      if (!contentType?.includes('application/json')) {
        throw new Error('Received non-JSON response from server');
      }

      const result = await response.json();
      setData(result);
    } catch (err: any) {
      console.error('Error fetching graph data:', err);
      setError(err.message || 'An error occurred while loading the graph');
    } finally {
      setLoading(false);
    }
  }, [centerNodeId, isOpen]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, loading, error, refresh: fetchData };
};
