import type { ReactNode } from 'react';

type Tone = 'neutral' | 'ember' | 'info' | 'go' | 'caution' | 'danger' | 'violet';

const TONE: Record<Tone, string> = {
  neutral: 'border-hair bg-surface-3 text-dim',
  ember: 'border-ember/40 bg-ember/10 text-ember',
  info: 'border-info/40 bg-info/10 text-info',
  go: 'border-go/40 bg-go/10 text-go',
  caution: 'border-caution/40 bg-caution/10 text-caution',
  danger: 'border-danger/40 bg-danger/10 text-danger',
  violet: 'border-violet/40 bg-violet/10 text-violet',
};

interface Props {
  tone?: Tone;
  icon?: ReactNode;
  className?: string;
  children: ReactNode;
}

/** Small pill used for statuses, FIA verdicts, source provenance, etc. */
export function Badge({ tone = 'neutral', icon, className = '', children }: Props) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium ${TONE[tone]} ${className}`}
    >
      {icon}
      {children}
    </span>
  );
}
