import type { TriageCode } from './types';

export const TRIAGE_LABEL: Record<TriageCode, string> = {
  RED: 'Codice Rosso',
  YELLOW: 'Codice Giallo',
  GREEN: 'Codice Verde',
  WHITE: 'Codice Bianco',
};

export const TRIAGE_SUBTITLE: Record<TriageCode, string> = {
  RED: 'Emergenza · Intervento immediato',
  YELLOW: 'Urgenza · Entro 15 minuti',
  GREEN: 'Differibile · Entro 2 ore',
  WHITE: 'Non urgente · Entro 24 ore',
};

export interface TriageVisualTokens {
  bar: string;
  chip: string;
  textOnSurface: string;
  border: string;
  ring: string;
  dot: string;
}

export const TRIAGE_TOKENS: Record<TriageCode, TriageVisualTokens> = {
  RED: {
    bar: 'bg-triage-red',
    chip: 'bg-triage-red text-white',
    textOnSurface: 'text-triage-red',
    border: 'border-triage-red/40',
    ring: 'ring-triage-red/30',
    dot: 'bg-triage-red',
  },
  YELLOW: {
    bar: 'bg-triage-yellow',
    chip: 'bg-triage-yellow text-triage-yellow-ink',
    textOnSurface: 'text-triage-yellow-ink dark:text-triage-yellow',
    border: 'border-triage-yellow/50',
    ring: 'ring-triage-yellow/30',
    dot: 'bg-triage-yellow',
  },
  GREEN: {
    bar: 'bg-triage-green',
    chip: 'bg-triage-green text-white',
    textOnSurface: 'text-triage-green',
    border: 'border-triage-green/40',
    ring: 'ring-triage-green/30',
    dot: 'bg-triage-green',
  },
  WHITE: {
    bar: 'bg-triage-white',
    chip: 'bg-triage-white-soft text-triage-white-ink',
    textOnSurface: 'text-ink-500 dark:text-ink-300',
    border: 'border-ink-200/80 dark:border-ink-700/60',
    ring: 'ring-ink-200',
    dot: 'bg-ink-300',
  },
};
