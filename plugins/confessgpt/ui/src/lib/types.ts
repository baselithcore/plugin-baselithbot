// Phases of the Roman Rite of Reconciliation, matching the backend enum
// in plugins/confessgpt/models.py.
export type RitePhase =
  | 'ACCOGLIENZA'
  | 'INVITO'
  | 'ASCOLTO'
  | 'ESORTAZIONE'
  | 'PENITENZA'
  | 'ATTO_DOLORE'
  | 'VERIFICA_CONTRIZIONE'
  | 'ASSOLUZIONE'
  | 'CONGEDO'
  | 'INVITO_RIFLESSIONE';

export interface TurnResponse {
  session_id: string;
  phase: RitePhase;
  utterance: string;
  next_phase: RitePhase;
  advance_on_user_reply: boolean;
  closed: boolean;
  audio_base64: string | null;
  audio_mime: string | null;
}

export interface SessionCreateResponse {
  session_id: string;
  opening_phase: 'ACCOGLIENZA';
}

export interface InfoResponse {
  plugin: string;
  version: string;
  voice_enabled: boolean;
  model_id: string | null;
  rite: string;
}

export type ConnState = 'idle' | 'active' | 'closed' | 'error';

export type Speaker = 'confessor' | 'penitent';

export interface DialogueTurn {
  id: string;
  speaker: Speaker;
  phase?: RitePhase;
  text: string;
  audioBase64?: string | null;
  audioMime?: string | null;
}
