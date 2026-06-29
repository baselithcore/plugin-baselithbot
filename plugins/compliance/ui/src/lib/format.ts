// Deadline / time formatting helpers for the regulatory reporting clock.

export type Urgency = 'ok' | 'warn' | 'danger';

/** Color band for a deadline given seconds remaining (negative = overdue). */
export function urgency(secondsRemaining: number): Urgency {
  if (secondsRemaining <= 0) return 'danger';
  if (secondsRemaining <= 6 * 3600) return 'danger'; // < 6h
  if (secondsRemaining <= 24 * 3600) return 'warn'; // < 24h
  return 'ok';
}

/** Compact "in 3h 20m" / "2d 4h" / "overdue 5h" label. */
export function remaining(dueAtISO: string, now: number = Date.now()): string {
  const diff = Math.round((new Date(dueAtISO).getTime() - now) / 1000);
  const abs = Math.abs(diff);
  const d = Math.floor(abs / 86400);
  const h = Math.floor((abs % 86400) / 3600);
  const m = Math.floor((abs % 3600) / 60);
  const parts = d > 0 ? `${d}d ${h}h` : h > 0 ? `${h}h ${m}m` : `${m}m`;
  return diff <= 0 ? `−${parts}` : parts;
}

/** Fraction of a window elapsed (0..1), for the meter fill. */
export function elapsedFraction(dueAtISO: string, windowSeconds: number, now = Date.now()): number {
  const remain = (new Date(dueAtISO).getTime() - now) / 1000;
  const used = (windowSeconds - remain) / windowSeconds;
  return Math.max(0, Math.min(1, used));
}

export function secondsTo(dueAtISO: string, now = Date.now()): number {
  return (new Date(dueAtISO).getTime() - now) / 1000;
}

export function dateTime(iso: string): string {
  return new Date(iso).toLocaleString();
}
