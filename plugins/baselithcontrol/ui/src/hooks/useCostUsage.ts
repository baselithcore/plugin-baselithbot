import { useEffect } from 'react';
import { fetchCostUsage } from '@/lib/api';
import { useControlStore } from '@/store/useControlStore';

const POLL_MS = 10000;

// Single shared poller for per-plugin LLM spend. Mounted once at the app root;
// cards and the plugin detail read their slice from the store (no per-card
// fetch). Failures are ignored — cost is supplementary, never blocks the UI.
export function useCostUsage(): void {
  const setCostUsage = useControlStore((s) => s.setCostUsage);

  useEffect(() => {
    let alive = true;
    const load = async () => {
      try {
        const view = await fetchCostUsage();
        if (alive) setCostUsage(view);
      } catch {
        /* ignore — cost is best-effort */
      }
    };
    void load();
    const id = setInterval(load, POLL_MS);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [setCostUsage]);
}
