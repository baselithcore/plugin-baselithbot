/**
 * useHoneypotSSE - Real-time SSE connection for live attack updates
 */

import { useEffect, useCallback, Dispatch, SetStateAction } from 'react';
import type {
  AttackEvent,
  HoneypotStats,
  HoneypotProtocol,
  AttackCategory,
  AttackSeverity,
  HoneypotInfo,
} from '../../types';

import type { DiscoveryLog } from '../../types';

interface UseHoneypotSSEOptions {
  setEvents: Dispatch<SetStateAction<AttackEvent[]>>;
  setStats: Dispatch<SetStateAction<HoneypotStats | null>>;
  setLogs: Dispatch<SetStateAction<DiscoveryLog[]>>;
  setHoneypots?: Dispatch<SetStateAction<HoneypotInfo[]>>;
}

/**
 * Hook for managing SSE connection to receive live attack events
 */
export function useHoneypotSSE({
  setEvents,
  setStats,
  setLogs,
  setHoneypots,
}: UseHoneypotSSEOptions): void {
  const handleAttackEvent = useCallback(
    (payload: any) => {
      if (!payload.data) return;

      const newEvent: AttackEvent = {
        event_id: payload.data.id || crypto.randomUUID(),
        session_id: payload.data.session_id || '',
        honeypot_id: payload.data.honeypot_id || 'default',
        protocol: (payload.data.protocol?.toLowerCase() || 'tcp') as HoneypotProtocol,
        timestamp: payload.data.timestamp || new Date().toISOString(),
        source_ip: payload.data.source_ip || 'unknown',
        source_port: 0,
        geo: payload.data.source
          ? {
              country: payload.data.source.country || null,
              country_code: payload.data.source.country_code || null,
              city: payload.data.source.city || null,
              latitude: payload.data.source.lat || null,
              longitude: payload.data.source.lng || null,
            }
          : null,
        event_type: 'attack',
        raw_data: '',
        username: null,
        password: null,
        command: payload.data.command || null,
        http_method: null,
        http_path: payload.data.http_path || null,
        http_headers: null,
        http_body: null,
        detected_patterns: payload.data.patterns || [],
        category: (payload.data.category || 'unknown') as AttackCategory,
        severity: (payload.data.severity || 'info') as AttackSeverity,
        ai_classification: null,
        matched_cves: [],
        matched_cwes: [],
        correlation_confidence: null,
        // Bot detection fields (from SSE or null for real-time)
        is_bot: payload.data.is_bot ?? null,
        bot_confidence: payload.data.bot_confidence ?? null,
        bot_classification: payload.data.bot_classification ?? null,
        bot_signals: payload.data.bot_signals ?? null,
      };

      // Prepend new event to the list (avoid duplicates)
      setEvents((prev) => {
        if (prev.some((e) => e.event_id === newEvent.event_id)) {
          return prev;
        }
        return [newEvent, ...prev].slice(0, 100); // Keep max 100 events
      });

      // Update global stats incrementally
      setStats((prev) =>
        prev
          ? {
              ...prev,
              total_events: prev.total_events + 1,
            }
          : prev
      );

      // Update individual honeypot stats
      if (setHoneypots) {
        setHoneypots((prev) =>
          prev.map((hp) => {
            if (hp.id === newEvent.honeypot_id) {
              return {
                ...hp,
                total_events: hp.total_events + 1,
                // Simple heuristic for active attackers: increment if IP is new to us (not robust client-side)
                // or just increment for visual feedback.
                // For now, we'll just increment active_attackers to show activity,
                // treating each new attack as potentially a new active session/attacker momentarily.
                active_attackers: hp.active_attackers + 1,
              };
            }
            return hp;
          })
        );
      }

      // Synthesize log entry for Live Attack Feed
      const logMessage = `[${newEvent.protocol.toUpperCase()}] Attack from ${newEvent.source_ip}: ${newEvent.event_type} (${newEvent.severity})`;
      const newLog: any = {
        timestamp: newEvent.timestamp,
        message: logMessage,
        is_alert: newEvent.severity === 'critical' || newEvent.severity === 'high',
        is_error: false,
      };

      setLogs((prev) => [...prev, newLog].slice(-100)); // Keep last 100 logs
    },
    [setEvents, setStats, setLogs, setHoneypots]
  );

  useEffect(() => {
    // Use /api prefix for Vite proxy to correctly route to backend
    const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api';
    let eventSource: EventSource | null = null;
    let reconnectTimer: ReturnType<typeof setTimeout> | null = null;

    const connectSSE = () => {
      // Get token from storage (same key as used in auth provider)
      const token = localStorage.getItem('auth_access_token');
      const url = token
        ? `${API_BASE}/honeypot/stream/attacks?include_history=false&token=${token}`
        : `${API_BASE}/honeypot/stream/attacks?include_history=false`;

      eventSource = new EventSource(url);

      eventSource.addEventListener('connected', () => {
        console.log('[HoneypotPanel] SSE connected for real-time updates');
      });

      eventSource.addEventListener('attack', (event) => {
        try {
          // console.debug('[HoneypotPanel] SSE Attack:', event.data);
          const payload = JSON.parse(event.data);
          handleAttackEvent(payload);
        } catch (err) {
          console.error('[HoneypotPanel] Failed to parse SSE event:', err);
        }
      });

      eventSource.addEventListener('log', (event) => {
        try {
          console.debug('[HoneypotPanel] SSE Log received:', event.data);
          const payload = JSON.parse(event.data);
          const newLog: DiscoveryLog = {
            timestamp: payload.data.timestamp || new Date().toISOString(),
            message: payload.data.message || 'Unknown log message',
            is_alert: payload.data.is_alert || false,
            is_error: payload.data.is_error || false,
            agent_type: payload.data.agent_type || 'system',
            severity: 'info', // Default
          };
          setLogs((prev) => [...prev, newLog].slice(-100));
        } catch (err) {
          console.error('[HoneypotPanel] Failed to parse SSE log:', err);
        }
      });

      eventSource.onerror = () => {
        console.warn('[HoneypotPanel] SSE connection error, reconnecting in 5s...');
        eventSource?.close();
        reconnectTimer = setTimeout(connectSSE, 5000);
      };
    };

    connectSSE();

    return () => {
      eventSource?.close();
      if (reconnectTimer) clearTimeout(reconnectTimer);
    };
  }, [handleAttackEvent]);
}
