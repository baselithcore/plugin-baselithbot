export type Rating = 'up' | 'down';

export interface Feedback {
  rating: Rating;
  reason?: string;
  at: number;
}

const STORAGE_KEY = 'llm-wiki:feedback';

function readAll(): Record<string, Feedback> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as Record<string, Feedback>) : {};
  } catch {
    return {};
  }
}

function writeAll(data: Record<string, Feedback>) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch {
    /* storage disabled */
  }
}

export function getFeedback(messageId: string): Feedback | null {
  return readAll()[messageId] ?? null;
}

export function setFeedback(messageId: string, fb: Feedback | null) {
  const all = readAll();
  if (fb === null) delete all[messageId];
  else all[messageId] = fb;
  writeAll(all);
}

/**
 * Motivi preset per voto negativo — utili per triage qualitativo.
 * Aggiornati a dominio assicurativo/legale.
 */
export const DOWN_REASONS: { id: string; label: string }[] = [
  { id: 'factual', label: 'Fattualmente sbagliato' },
  { id: 'hallucinated', label: 'Cita fonte inesistente' },
  { id: 'missing-article', label: 'Claim senza riferimento articolo' },
  { id: 'missing-exclusion', label: "Manca l'esclusione rilevante" },
  { id: 'wrong-edition', label: 'Edizione sbagliata' },
  { id: 'franchigia-vs-scoperto', label: 'Confonde franchigia e scoperto' },
  { id: 'incomplete', label: 'Incompleto' },
  { id: 'other', label: 'Altro' },
];
