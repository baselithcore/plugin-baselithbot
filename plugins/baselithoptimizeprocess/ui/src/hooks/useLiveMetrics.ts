import { useEffect, useState } from 'react';

import { api } from '../api/client';
import type { Bottleneck, KpiSnapshot, MetricsEvent } from '../api/types';

export interface LiveMetrics {
  snapshots: KpiSnapshot[];
  bottlenecks: Bottleneck[];
  connected: boolean;
}

/**
 * Subscribe to the backend SSE feed for a process and expose the latest
 * snapshots/bottlenecks. Seeds from the REST snapshot endpoints on mount so the
 * view is populated before the first streamed event arrives.
 */
export function useLiveMetrics(processId: string | null): LiveMetrics {
  const [snapshots, setSnapshots] = useState<KpiSnapshot[]>([]);
  const [bottlenecks, setBottlenecks] = useState<Bottleneck[]>([]);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!processId) {
      setSnapshots([]);
      setBottlenecks([]);
      setConnected(false);
      return;
    }

    let cancelled = false;
    void Promise.all([api.snapshots(processId), api.bottlenecks(processId)])
      .then(([snaps, necks]) => {
        if (cancelled) return;
        setSnapshots(snaps);
        setBottlenecks(necks);
      })
      .catch(() => undefined);

    const source = new EventSource(api.streamUrl(processId));
    source.onopen = () => setConnected(true);
    source.onerror = () => setConnected(false);
    source.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data) as MetricsEvent;
        if (payload.type === 'metrics') {
          setSnapshots(payload.snapshots);
          setBottlenecks(payload.bottlenecks);
        }
      } catch {
        // ignore malformed frames
      }
    };

    return () => {
      cancelled = true;
      source.close();
    };
  }, [processId]);

  return { snapshots, bottlenecks, connected };
}
