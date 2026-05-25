import { useState, useCallback } from 'react';
import { fetchKbCounts } from '../../api/client';

export const useKbCounts = () => {
  const [counts, setCounts] = useState<Record<string, { stories: number; test_cases: number }>>({});
  const [countsLoading, setCountsLoading] = useState<Record<string, boolean>>({});

  const loadCounts = async (label: string) => {
    setCounts((prev) => {
      const next = { ...prev };
      delete next[label];
      return next;
    });
    setCountsLoading((prev) => ({ ...prev, [label]: true }));

    try {
      const res = await fetchKbCounts(label);
      setCounts((prev) => ({ ...prev, [label]: res }));
    } catch (err) {
      console.error('KbPanel: Fetch error', err);
      setCounts((prev) => ({
        ...prev,
        [label]: { stories: 0, test_cases: 0 },
      }));
    } finally {
      setCountsLoading((prev) => ({ ...prev, [label]: false }));
    }
  };

  const resetCounts = useCallback(() => setCounts({}), []);

  return { counts, countsLoading, loadCounts, resetCounts };
};
