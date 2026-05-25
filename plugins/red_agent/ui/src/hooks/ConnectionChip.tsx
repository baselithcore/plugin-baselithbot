import { useEffect, useState } from 'react';
import { Chip } from '../components/ui';

/**
 * Status chip for ``useActivityStream``: shows live / polling /
 * reconnecting (with seconds-to-next-attempt countdown). Pure
 * presentational — owns its own 1Hz timer so the parent doesn't have
 * to re-render the whole card.
 */
export function ConnectionChip({
  connected,
  nextRetryAt,
  fallbackLabel = 'polling',
}: {
  connected: boolean;
  nextRetryAt: number | null;
  fallbackLabel?: string;
}) {
  const [, setTick] = useState(0);
  useEffect(() => {
    if (connected || nextRetryAt === null) return;
    const id = window.setInterval(() => setTick((t) => t + 1), 1000);
    return () => window.clearInterval(id);
  }, [connected, nextRetryAt]);

  if (connected) {
    return (
      <Chip tone="good">
        <span className="mr-1 inline-block h-1.5 w-1.5 rounded-full bg-status-success" />
        live
      </Chip>
    );
  }
  if (nextRetryAt !== null) {
    const remaining = Math.max(0, Math.round((nextRetryAt - Date.now()) / 1000));
    return (
      <Chip tone="warn">
        <span className="mr-1 inline-block h-1.5 w-1.5 rounded-full bg-accent-warn animate-pulse" />
        retry {remaining}s
      </Chip>
    );
  }
  return (
    <Chip tone="neutral">
      <span className="mr-1 inline-block h-1.5 w-1.5 rounded-full bg-text-subtle" />
      {fallbackLabel}
    </Chip>
  );
}
