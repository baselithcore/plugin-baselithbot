/**
 * Streaming APIs
 * Real-time attack streaming via Server-Sent Events (SSE)
 */

import { honeypotApiFetch } from './core';
import type { GeoAttack } from './geo';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';

export interface StreamStatus {
  subscribers: number;
  history_size: number;
}

export async function fetchStreamStatus(): Promise<StreamStatus> {
  return honeypotApiFetch<StreamStatus>('/stream/status');
}

/**
 * Create an EventSource connection for real-time attack streaming
 */
export function createAttackStream(
  onAttack: (data: GeoAttack) => void,
  onError?: (error: Event) => void
): EventSource {
  const eventSource = new EventSource(`${API_BASE}/honeypot/stream/attacks`, {
    withCredentials: true, // Include cookies for auth
  });

  eventSource.addEventListener('attack', (event) => {
    try {
      const data = JSON.parse(event.data);
      if (data.data) {
        onAttack(data.data);
      }
    } catch (err) {
      console.error('Failed to parse attack event:', err);
    }
  });

  if (onError) {
    eventSource.onerror = onError;
  }

  return eventSource;
}
