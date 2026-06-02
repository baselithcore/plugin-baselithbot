// API client for ConfessGPT.
//
// All network traffic carries no persistent identity: the session id
// returned by the backend is opaque and is wiped at end-of-rite or on
// page unload. We never store it in localStorage / cookies.

import type { InfoResponse, SessionCreateResponse, TurnResponse } from './types';

const BASE = '/api/confessgpt';

async function jsonOrThrow<T>(res: Response): Promise<T> {
  if (!res.ok) {
    if (res.status === 404 || res.status === 410) {
      throw new SessionClosedError('La sessione è stata sigillata.');
    }
    throw new Error(`Errore di rete (${res.status})`);
  }
  return (await res.json()) as T;
}

export class SessionClosedError extends Error {}

export async function fetchInfo(): Promise<InfoResponse> {
  const res = await fetch(`${BASE}/info`);
  return jsonOrThrow<InfoResponse>(res);
}

export async function openSession(voiceEnabled: boolean): Promise<SessionCreateResponse> {
  const res = await fetch(`${BASE}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ voice_enabled: voiceEnabled }),
  });
  return jsonOrThrow<SessionCreateResponse>(res);
}

export async function postTurn(sessionId: string, utterance: string): Promise<TurnResponse> {
  const res = await fetch(`${BASE}/turn`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, utterance }),
  });
  return jsonOrThrow<TurnResponse>(res);
}

export async function postVoiceTurn(sessionId: string, audioBase64: string): Promise<TurnResponse> {
  const res = await fetch(`${BASE}/voice/turn`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      utterance: '',
      audio_base64: audioBase64,
    }),
  });
  return jsonOrThrow<TurnResponse>(res);
}

export async function closeSession(sessionId: string): Promise<void> {
  try {
    await fetch(`${BASE}/sessions/${encodeURIComponent(sessionId)}`, {
      method: 'DELETE',
      keepalive: true,
    });
  } catch {
    // Best-effort: server already wipes on its own schedule too.
  }
}
