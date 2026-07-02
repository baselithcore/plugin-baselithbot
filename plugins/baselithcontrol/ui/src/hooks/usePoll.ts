import { useEffect, useRef } from 'react';

export interface PollOptions {
  /** Base interval between successful ticks, in ms. */
  intervalMs: number;
  /** When false, the poller is fully stopped (no timers, no listeners). */
  enabled?: boolean;
  /** Cap on the error backoff, as a multiple of `intervalMs` (default 8×). */
  maxBackoff?: number;
  /** Re-run (and refetch immediately) when this changes, e.g. a filter key. */
  key?: string;
}

/**
 * Shared polling loop with hygiene built in: runs `tick` immediately and then
 * on an interval, pauses entirely while the document is hidden (refetching as
 * soon as it becomes visible again) and applies capped exponential backoff on
 * consecutive failures (reset on the first success).
 *
 * `tick` receives an `alive()` guard — false once the effect has been torn
 * down (unmount or `key` change) — so an in-flight response for stale inputs
 * can be dropped instead of overwriting fresher state. It resolves `true` on
 * success and `false` on failure; rejections count as failures.
 */
export function usePoll(
  tick: (alive: () => boolean) => Promise<boolean>,
  { intervalMs, enabled = true, maxBackoff = 8, key = '' }: PollOptions
): void {
  // Always call the latest tick without making it an effect dependency.
  const tickRef = useRef(tick);
  tickRef.current = tick;

  useEffect(() => {
    if (!enabled) return;
    let alive = true;
    let failures = 0;
    let timer: number | undefined;
    const isAlive = () => alive;

    const schedule = () => {
      timer = window.setTimeout(run, intervalMs * Math.min(2 ** failures, maxBackoff));
    };

    const run = async () => {
      if (!alive) return;
      // Hidden tab → stop the loop; the visibility listener resumes it.
      if (document.hidden) return;
      const ok = await tickRef.current(isAlive).catch(() => false);
      if (!alive) return;
      failures = ok ? 0 : failures + 1;
      schedule();
    };

    const onVisible = () => {
      if (!document.hidden && alive) {
        window.clearTimeout(timer);
        void run();
      }
    };
    document.addEventListener('visibilitychange', onVisible);
    void run();

    return () => {
      alive = false;
      window.clearTimeout(timer);
      document.removeEventListener('visibilitychange', onVisible);
    };
    // `key` re-runs the effect for new filters/inputs (immediate refetch).
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, intervalMs, maxBackoff, key]);
}
