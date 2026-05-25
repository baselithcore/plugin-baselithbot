import type { Severity } from '@/lib/api';

export type SevFloor = 'INFO' | 'WARN' | 'FAIL';

export interface ScanProfile {
  lang: string;
  severityFloor: SevFloor;
  confidenceMin: number;
  includePass: boolean;
  groupByPolicy: boolean;
}

export const FLOOR_RANK: Record<Severity, number> = {
  FAIL: 3,
  WARN: 2,
  INFO: 1,
  PASS: 0,
};

export const DEFAULT_PROFILE: ScanProfile = {
  lang: '',
  severityFloor: 'INFO',
  confidenceMin: 0,
  includePass: false,
  groupByPolicy: false,
};

export const LANGS = [
  { code: '', label: 'Auto-detect' },
  { code: 'it', label: 'Italian' },
  { code: 'en', label: 'English' },
  { code: 'fr', label: 'French' },
  { code: 'de', label: 'German' },
  { code: 'es', label: 'Spanish' },
];
