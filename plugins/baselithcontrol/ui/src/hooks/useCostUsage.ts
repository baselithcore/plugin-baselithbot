import { fetchCostUsage } from '@/lib/api';
import { usePoll } from '@/hooks/usePoll';
import { useControlStore } from '@/store/useControlStore';

const POLL_MS = 10000;

// Single shared poller for per-plugin LLM spend. Mounted once at the app root;
// cards and the plugin detail read their slice from the store (no per-card
// fetch). Failures are ignored — cost is supplementary, never blocks the UI.
export function useCostUsage(): void {
  const setCostUsage = useControlStore((s) => s.setCostUsage);

  usePoll(
    async (alive) => {
      try {
        const view = await fetchCostUsage();
        if (alive()) setCostUsage(view);
        return true;
      } catch {
        return false; // best-effort — backoff handles persistent failures
      }
    },
    { intervalMs: POLL_MS }
  );
}
