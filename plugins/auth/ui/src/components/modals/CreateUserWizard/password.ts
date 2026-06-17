/**
 * Password helpers for the create-user wizard: a cryptographically-random
 * generator and a lightweight strength heuristic (no external deps).
 */

const ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%^&*?';

/** Generate a strong random password using the Web Crypto API. */
export function generatePassword(length = 20): string {
  const out: string[] = [];
  const buf = new Uint32Array(length);
  crypto.getRandomValues(buf);
  for (let i = 0; i < length; i++) {
    out.push(ALPHABET[buf[i] % ALPHABET.length]);
  }
  return out.join('');
}

export interface Strength {
  /** 0..4 score. */
  score: number;
  /** i18n key suffix: weak | fair | good | strong. */
  level: 'empty' | 'weak' | 'fair' | 'good' | 'strong';
}

/**
 * Heuristic strength: rewards length and character-class diversity. Tuned to
 * mirror the backend policy (length + variety) without shipping a 400 KB
 * estimator into the bundle.
 */
export function scorePassword(pw: string): Strength {
  if (!pw) return { score: 0, level: 'empty' };

  let score = 0;
  if (pw.length >= 8) score++;
  if (pw.length >= 12) score++;
  if (pw.length >= 16) score++;

  const classes = [/[a-z]/, /[A-Z]/, /[0-9]/, /[^A-Za-z0-9]/].filter((re) => re.test(pw)).length;
  if (classes >= 2) score++;
  if (classes >= 3) score++;

  // Penalise trivial repetition / sequences.
  if (/(.)\1{2,}/.test(pw)) score--;

  const clamped = Math.max(0, Math.min(4, score));
  const level = (['weak', 'weak', 'fair', 'good', 'strong'] as const)[clamped];
  return { score: clamped, level };
}

export const STRENGTH_COLORS: Record<Strength['level'], string> = {
  empty: 'var(--admin-border)',
  weak: 'var(--admin-error)',
  fair: 'var(--admin-warning)',
  good: '#3b82f6',
  strong: 'var(--admin-success)',
};
