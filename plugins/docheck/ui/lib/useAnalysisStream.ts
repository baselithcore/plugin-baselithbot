'use client';

import { useEffect, useState } from 'react';
import { notify } from './notifications';

const WS_BASE = process.env.NEXT_PUBLIC_WS_BASE ?? 'ws://127.0.0.1:8765/api/v1/ws/analysis';

export type AnalysisEvent =
  | { type: 'phase'; phase: string; doc_id?: string }
  | { type: 'progress'; current: number; total: number; label?: string }
  | { type: 'finding'; finding: unknown }
  | { type: 'trace'; step: unknown }
  | { type: 'report'; report_id: string }
  | { type: 'error'; code: string; message: string };

interface State {
  phase: string;
  progress: { current: number; total: number; label?: string } | null;
  events: AnalysisEvent[];
  done: boolean;
  error: string | null;
}

const INITIAL: State = {
  phase: 'idle',
  progress: null,
  events: [],
  done: false,
  error: null,
};

export function useAnalysisStream(docId: string | null, enabled = true): State {
  const [state, setState] = useState<State>(INITIAL);

  useEffect(() => {
    if (!docId || !enabled) {
      setState({ ...INITIAL, done: !enabled });
      return;
    }

    let opened = false;
    let manuallyClosed = false;
    const ws = new WebSocket(`${WS_BASE}/${docId}`);
    setState({ ...INITIAL, phase: 'connecting' });

    ws.onopen = () => {
      opened = true;
      setState((s) => ({ ...s, phase: 'subscribed' }));
    };
    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data) as AnalysisEvent;
        setState((s) => ({
          ...s,
          events: [...s.events, data],
          phase: data.type === 'phase' ? data.phase : s.phase,
          progress:
            data.type === 'progress'
              ? { current: data.current, total: data.total, label: data.label }
              : s.progress,
          done: data.type === 'phase' && data.phase === 'done',
        }));
        if (data.type === 'phase' && data.phase === 'done') {
          notify({
            tone: 'success',
            title: 'Analysis complete',
            body: `Document ${docId} ready for review`,
            href: '/',
            source: 'analysis',
          });
        } else if (data.type === 'error') {
          notify({
            tone: 'danger',
            title: `Analysis error: ${data.code}`,
            body: data.message,
            source: 'analysis',
          });
        }
      } catch {
        /* ignore malformed */
      }
    };
    ws.onerror = () => {
      // Surface only genuine connect failures. After a successful open, a
      // dropped socket (server reload, network blip) reaches us via
      // ``onclose`` first and is treated as a normal end-of-stream.
      if (!opened && !manuallyClosed) {
        setState((s) => ({ ...s, error: 'ws_connect_failed', done: true }));
      }
    };
    ws.onclose = () => setState((s) => ({ ...s, done: true }));

    return () => {
      manuallyClosed = true;
      ws.close();
    };
  }, [docId, enabled]);

  return state;
}
