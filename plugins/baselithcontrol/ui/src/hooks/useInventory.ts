import { useCallback, useEffect, useState } from 'react';
import { fetchInventory } from '@/lib/api';
import { useControlStore } from '@/store/useControlStore';

interface InventoryHook {
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

// Fetch the inventory once on mount; the SSE stream keeps it fresh afterwards.
export function useInventory(): InventoryHook {
  const setInventory = useControlStore((s) => s.setInventory);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const inv = await fetchInventory();
      setInventory(inv.plugins);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'failed');
    } finally {
      setLoading(false);
    }
  }, [setInventory]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  return { loading, error, refresh };
}
