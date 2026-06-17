// Shared visual mappings for race-domain concepts (urgency, tyres, severity).

export type Tone = 'ember' | 'info' | 'go' | 'caution' | 'danger' | 'violet' | 'neutral';

/** Recommendation kind → urgency tone. Red is reserved for true urgency. */
export function kindTone(kind: string): Tone {
  switch (kind) {
    case 'pit_now':
      return 'danger';
    case 'pit_vsc':
    case 'pit_wet':
      return 'caution';
    case 'push':
    case 'engine_mode':
      return 'ember';
    case 'conserve':
      return 'go';
    case 'stay_out':
      return 'info';
    default:
      return 'neutral';
  }
}

/** Tyre compound → broadcast-style colour code. */
export function compoundStyle(compound: string): { tone: Tone; letter: string } {
  const c = compound.toUpperCase();
  if (c.startsWith('S')) return { tone: 'danger', letter: 'S' };
  if (c.startsWith('M')) return { tone: 'caution', letter: 'M' };
  if (c.startsWith('H')) return { tone: 'neutral', letter: 'H' };
  if (c.startsWith('I')) return { tone: 'go', letter: 'I' };
  if (c.startsWith('W')) return { tone: 'info', letter: 'W' };
  return { tone: 'neutral', letter: c.slice(0, 1) || '?' };
}

export const SEVERITY_TONE: Record<string, Tone> = {
  low: 'neutral',
  medium: 'info',
  high: 'caution',
  critical: 'danger',
};

/** Wear ratio → tone (green safe, amber watch, red critical). */
export function wearTone(wear: number): 'danger' | 'caution' | 'go' {
  return wear > 0.78 ? 'danger' : wear > 0.5 ? 'caution' : 'go';
}
