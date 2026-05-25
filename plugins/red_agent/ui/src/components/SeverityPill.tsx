import type { Severity } from '../lib/api';

const SHAPE: Record<Severity, string> = {
  info: '▢',
  low: '◇',
  medium: '△',
  high: '▲',
  critical: '⬢',
};

export function SeverityPill({ severity }: { severity: Severity }) {
  return (
    <span className={`sev-pill ${severity}`} aria-label={`severity ${severity}`}>
      <span aria-hidden>{SHAPE[severity]}</span>
      {severity.toUpperCase()}
    </span>
  );
}
