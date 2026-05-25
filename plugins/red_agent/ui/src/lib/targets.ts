import type { ReactNode } from 'react';
import type { Severity, TargetKind, TargetPosture, TargetRecord } from './api';

export interface KindMeta {
  label: string;
  shortLabel: string;
  description: string;
  accent: string;
  hint: string;
  comingSoon?: boolean;
}

export const KIND_META: Record<TargetKind, KindMeta> = {
  web: {
    label: 'Web Application',
    shortLabel: 'Web',
    description: 'URLs, APIs and externally exposed services.',
    accent: 'from-cyan-500/10 to-blue-500/5 ring-cyan-500/30 text-cyan-300',
    hint: 'https://api.example.com',
  },
  cloud: {
    label: 'Cloud Account',
    shortLabel: 'Cloud',
    description: 'AWS, GCP or Azure account audited via read-only role.',
    accent: 'from-violet-500/10 to-fuchsia-500/5 ring-violet-500/30 text-violet-300',
    hint: 'aws:account/123456789012',
  },
  network: {
    label: 'Network Range',
    shortLabel: 'Network',
    description: 'IP, CIDR or internal subnet.',
    accent: 'from-emerald-500/10 to-teal-500/5 ring-emerald-500/30 text-emerald-300',
    hint: '10.0.0.0/24',
  },
  host: {
    label: 'Host (agent)',
    shortLabel: 'Host',
    description: 'Linux / macOS endpoint reached via the enrolled Red Agent daemon.',
    accent: 'from-amber-500/10 to-orange-500/5 ring-amber-500/30 text-amber-300',
    hint: 'agent:<uuid>',
  },
  repo: {
    label: 'Repository',
    shortLabel: 'Repo',
    description: 'Source code or IaC tree audited via SAST, SCA, secret and IaC scanners.',
    accent: 'from-pink-500/10 to-rose-500/5 ring-pink-500/30 text-pink-300',
    hint: '/path/to/repo or git@github.com:org/repo.git',
  },
  binary: {
    label: 'Binary',
    shortLabel: 'Binary',
    description: 'Uploaded executable / artifact analyzed by the static binary scanner.',
    accent: 'from-slate-500/10 to-zinc-500/5 ring-slate-500/30 text-slate-300',
    hint: 'sha256 of an artifact in the binary store',
    comingSoon: true,
  },
};

export const KIND_ORDER: TargetKind[] = ['web', 'cloud', 'network', 'host', 'repo', 'binary'];

const SEV_WEIGHTS: Record<Severity, number> = {
  critical: 10,
  high: 5,
  medium: 2,
  low: 0.5,
  info: 0.1,
};

export function postureRiskScore(p: TargetPosture | undefined): number {
  if (!p) return 100;
  const sev = p.severity_counts ?? {};
  const weighted =
    (sev.critical ?? 0) * SEV_WEIGHTS.critical +
    (sev.high ?? 0) * SEV_WEIGHTS.high +
    (sev.medium ?? 0) * SEV_WEIGHTS.medium +
    (sev.low ?? 0) * SEV_WEIGHTS.low;
  const overduePenalty = Math.min(20, p.overdue * 2);
  return Math.max(0, Math.min(100, Math.round(100 - weighted - overduePenalty)));
}

export function riskBand(score: number): {
  label: string;
  tone: 'success' | 'neutral' | 'warn' | 'critical';
} {
  if (score >= 85) return { label: 'Healthy', tone: 'success' };
  if (score >= 65) return { label: 'Watch', tone: 'neutral' };
  if (score >= 40) return { label: 'At risk', tone: 'warn' };
  return { label: 'Critical', tone: 'critical' };
}

export function targetDisplayLabel(t: TargetRecord): ReactNode {
  return t.name || t.value;
}

export function shortId(id: string, n = 8): string {
  return id.slice(0, n);
}
