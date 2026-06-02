import type { Severity } from '../../../lib/api';

export function relTime(iso: string | null): string {
  if (!iso) return '—';
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}

export function riskTone(score: number): 'critical' | 'warn' | 'brand' | 'neutral' {
  if (score >= 9) return 'critical';
  if (score >= 7) return 'warn';
  if (score >= 4) return 'brand';
  return 'neutral';
}

export function severityHeaderCls(s: Severity): string {
  switch (s) {
    case 'critical':
      return 'border-sev-critical/40 bg-gradient-to-r from-sev-critical/15 to-transparent';
    case 'high':
      return 'border-accent-warn/40 bg-gradient-to-r from-accent-warn/15 to-transparent';
    case 'medium':
      return 'border-sev-medium/40 bg-gradient-to-r from-sev-medium/15 to-transparent';
    case 'low':
      return 'border-sev-low/40 bg-gradient-to-r from-sev-low/15 to-transparent';
    default:
      return 'border-bg-line bg-gradient-to-r from-bg-overlay to-transparent';
  }
}

export function pickEntries(
  data: Record<string, unknown>,
  keys: string[],
  rendered: Set<string>
): [string, unknown][] {
  const out: [string, unknown][] = [];
  for (const key of keys) {
    if (!(key in data)) continue;
    rendered.add(key);
    out.push([key, data[key]]);
  }
  return out;
}

export function evidenceStatus(data: Record<string, unknown>): {
  label: string;
  tone: 'neutral' | 'brand' | 'warn' | 'critical' | 'good';
} {
  if (data.scanner_failure) return { label: 'Scanner failure', tone: 'warn' };
  if (data.confirmed) return { label: 'Confirmed', tone: 'good' };
  const triage = data.triage_llm;
  if (isRecord(triage) && typeof triage.verdict === 'string') {
    const verdict = triage.verdict.replace(/_/g, ' ');
    return {
      label: verdict,
      tone: verdict.includes('false') ? 'warn' : verdict.includes('confirmed') ? 'good' : 'brand',
    };
  }
  if ('ml_fp_score' in data) return { label: 'ML scored', tone: 'brand' };
  return { label: 'Captured', tone: 'neutral' };
}

export function formatEvidenceKey(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (m) => m.toUpperCase());
}

export function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export function isHttpUrl(value: string): boolean {
  return /^https?:\/\//i.test(value);
}
