// Phase metadata for the linear rite progression. Kept in sync with
// plugins/confessgpt/models.py::RitePhase and the system prompt.

import type { RitePhase } from './types';

export interface PhaseDef {
  id: RitePhase;
  label: string;
  short: string;
}

// Linear chain — INVITO_RIFLESSIONE is the negative branch and is
// rendered in place of ASSOLUZIONE when the penitent refuses to
// repent. VERIFICA_CONTRIZIONE is internal and not displayed.
export const RITE_CHAIN: PhaseDef[] = [
  { id: 'ACCOGLIENZA', label: 'Accoglienza', short: 'Accoglienza' },
  { id: 'INVITO', label: 'Invito', short: 'Invito' },
  { id: 'ASCOLTO', label: 'Ascolto', short: 'Ascolto' },
  { id: 'ESORTAZIONE', label: 'Esortazione', short: 'Esortazione' },
  { id: 'PENITENZA', label: 'Penitenza', short: 'Penitenza' },
  { id: 'ATTO_DOLORE', label: 'Atto di Dolore', short: 'Atto Dolore' },
  { id: 'ASSOLUZIONE', label: 'Assoluzione', short: 'Assoluzione' },
  { id: 'CONGEDO', label: 'Congedo', short: 'Congedo' },
];

export const PHASE_LABELS: Record<RitePhase, string> = {
  ACCOGLIENZA: 'Accoglienza',
  INVITO: 'Invito',
  ASCOLTO: 'Ascolto',
  ESORTAZIONE: 'Esortazione',
  PENITENZA: 'Penitenza',
  ATTO_DOLORE: 'Atto di Dolore',
  VERIFICA_CONTRIZIONE: 'Verifica del cuore',
  ASSOLUZIONE: 'Assoluzione',
  CONGEDO: 'Congedo',
  INVITO_RIFLESSIONE: 'Invito alla riflessione',
};

export function phaseIndex(phase: RitePhase): number {
  return RITE_CHAIN.findIndex((p) => p.id === phase);
}

export function isTerminal(phase: RitePhase): boolean {
  return phase === 'CONGEDO' || phase === 'INVITO_RIFLESSIONE';
}

export function isRefusalBranch(phase: RitePhase): boolean {
  return phase === 'INVITO_RIFLESSIONE';
}

const ALLOWED_AUDIO_MIMES = new Set([
  'audio/mp3',
  'audio/mpeg',
  'audio/wav',
  'audio/ogg',
  'audio/webm',
  'audio/flac',
]);

export function sanitizeAudioMime(mime: string | null | undefined): string {
  if (typeof mime === 'string' && ALLOWED_AUDIO_MIMES.has(mime)) return mime;
  return 'audio/mp3';
}

// Whitelist before constructing data: URLs — XSS hardening.
export function isValidBase64(b64: string): boolean {
  return /^[A-Za-z0-9+/=\r\n]+$/.test(b64);
}
