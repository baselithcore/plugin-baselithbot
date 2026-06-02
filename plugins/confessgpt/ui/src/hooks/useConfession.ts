// Core confession state machine — a single hook orchestrates the
// whole rite. It encapsulates:
//
//  - session lifecycle (open / advance / close)
//  - dialogue transcript (in-memory, never persisted)
//  - phase tracking with terminal detection
//  - error surface (toast queue)
//
// Voice I/O is delegated to useVoiceRecording so this hook stays
// medium-concern.

import { useCallback, useEffect, useRef, useState } from 'react';
import { SessionClosedError, closeSession, openSession, postTurn, postVoiceTurn } from '../lib/api';
import { isTerminal } from '../lib/phases';
import type { DialogueTurn, RitePhase, TurnResponse } from '../lib/types';

export interface UseConfessionResult {
  sessionId: string | null;
  currentPhase: RitePhase;
  closed: boolean;
  pending: boolean;
  dialogue: DialogueTurn[];
  error: string | null;
  begin: () => Promise<void>;
  sayText: (text: string) => Promise<void>;
  sayVoice: (audioBase64: string) => Promise<void>;
  dismissError: () => void;
}

export function useConfession(): UseConfessionResult {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [currentPhase, setCurrentPhase] = useState<RitePhase>('ACCOGLIENZA');
  const [closed, setClosed] = useState(false);
  const [pending, setPending] = useState(false);
  const [dialogue, setDialogue] = useState<DialogueTurn[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Use a ref so concurrent calls cannot race the session id.
  const sidRef = useRef<string | null>(null);

  const pushTurn = useCallback((turn: DialogueTurn) => {
    setDialogue((prev) => [...prev, turn]);
  }, []);

  const applyServerTurn = useCallback(
    (data: TurnResponse) => {
      pushTurn({
        id: `c-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        speaker: 'confessor',
        phase: data.phase,
        text: data.utterance,
        audioBase64: data.audio_base64,
        audioMime: data.audio_mime,
      });
      setCurrentPhase(data.next_phase);
      if (data.closed) {
        setClosed(true);
        sidRef.current = null;
      }
    },
    [pushTurn]
  );

  const handleError = useCallback((err: unknown) => {
    if (err instanceof SessionClosedError) {
      setClosed(true);
      sidRef.current = null;
      setError('La sessione è stata sigillata. Ricarica per un nuovo rito.');
      return;
    }
    if (err instanceof Error) setError(err.message);
    else setError('Errore inatteso.');
  }, []);

  const begin = useCallback(async () => {
    if (sidRef.current || pending) return;
    setError(null);
    setPending(true);
    try {
      const session = await openSession(false);
      sidRef.current = session.session_id;
      setSessionId(session.session_id);
      // First turn — penitent says nothing, the priest opens.
      const data = await postTurn(session.session_id, '');
      applyServerTurn(data);
    } catch (err) {
      handleError(err);
    } finally {
      setPending(false);
    }
  }, [applyServerTurn, handleError, pending]);

  const sayText = useCallback(
    async (text: string) => {
      const sid = sidRef.current;
      if (!sid || pending) return;
      const trimmed = text.trim();
      if (!trimmed) return;

      pushTurn({
        id: `p-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        speaker: 'penitent',
        text: trimmed,
      });
      setPending(true);
      try {
        const data = await postTurn(sid, trimmed);
        applyServerTurn(data);
      } catch (err) {
        handleError(err);
      } finally {
        setPending(false);
      }
    },
    [applyServerTurn, handleError, pending, pushTurn]
  );

  const sayVoice = useCallback(
    async (audioBase64: string) => {
      const sid = sidRef.current;
      if (!sid || pending || !audioBase64) return;

      pushTurn({
        id: `p-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        speaker: 'penitent',
        text: '…',
      });
      setPending(true);
      try {
        const data = await postVoiceTurn(sid, audioBase64);
        applyServerTurn(data);
      } catch (err) {
        handleError(err);
      } finally {
        setPending(false);
      }
    },
    [applyServerTurn, handleError, pending, pushTurn]
  );

  const dismissError = useCallback(() => setError(null), []);

  // Auto-close on unmount / unload — sigillum hardening.
  useEffect(() => {
    const onUnload = () => {
      const sid = sidRef.current;
      if (sid) {
        sidRef.current = null;
        // Fire-and-forget — keepalive lets the request survive unload.
        void closeSession(sid);
      }
    };
    window.addEventListener('beforeunload', onUnload);
    return () => {
      window.removeEventListener('beforeunload', onUnload);
      onUnload();
    };
  }, []);

  // When a terminal phase arrives, ensure session id is gone even if
  // the server reported closed=true.
  useEffect(() => {
    if (isTerminal(currentPhase) && sidRef.current && closed) {
      sidRef.current = null;
    }
  }, [closed, currentPhase]);

  return {
    sessionId,
    currentPhase,
    closed,
    pending,
    dialogue,
    error,
    begin,
    sayText,
    sayVoice,
    dismissError,
  };
}
