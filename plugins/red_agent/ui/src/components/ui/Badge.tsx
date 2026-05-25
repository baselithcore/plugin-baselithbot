import { ReactNode } from 'react';
import type { Severity } from '../../lib/api';

const SEV_LABEL: Record<Severity, string> = {
  info: 'Info',
  low: 'Low',
  medium: 'Medium',
  high: 'High',
  critical: 'Critical',
};

export function SeverityBadge({ severity, full = false }: { severity: Severity; full?: boolean }) {
  return (
    <span className={`sev-pill ${severity}`} aria-label={`severity ${severity}`}>
      {full ? SEV_LABEL[severity] : severity.charAt(0).toUpperCase()}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const cls = status.toLowerCase().replace(/\s+/g, '_');
  return <span className={`status-pill ${cls}`}>{status.replace(/_/g, ' ')}</span>;
}

interface ChipProps {
  children: ReactNode;
  tone?: 'neutral' | 'brand' | 'warn' | 'critical' | 'good';
  className?: string;
}

const CHIP_TONE = {
  neutral: 'bg-bg-overlay text-text-secondary border-bg-line',
  brand: 'bg-brand/10 text-brand border-brand/30',
  warn: 'bg-accent-warn/10 text-accent-warn border-accent-warn/30',
  critical: 'bg-sev-critical/10 text-sev-critical border-sev-critical/30',
  good: 'bg-status-success/10 text-status-success border-status-success/30',
};

export function Chip({ children, tone = 'neutral', className = '' }: ChipProps) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded border px-2 py-0.5 text-xs font-mono ${CHIP_TONE[tone]} ${className}`}
    >
      {children}
    </span>
  );
}
