import type { Source } from '../../lib/types';

export type Rango = NonNullable<Source['rango']>;

export const LABEL_BY_RANGO: Record<string, string> = {
  'regolamento-ue': 'UE',
  'cc-inderogabile': 'CC inderog.',
  'cc-derogabile': 'CC',
  cap: 'CAP',
  'regolamento-ivass': 'Reg. IVASS',
  'circolare-ivass': 'Circ. IVASS',
  'condizioni-contrattuali': 'CdA',
  nta: 'NTA',
  'accordo-accessorio': 'App.',
  giurisprudenza: 'Giur.',
};

export function labelForRango(rango: Rango): string {
  return LABEL_BY_RANGO[rango] ?? rango;
}
