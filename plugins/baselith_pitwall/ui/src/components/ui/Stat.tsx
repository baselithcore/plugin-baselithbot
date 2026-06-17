import type { ReactNode } from 'react';

interface Props {
  label: string;
  value: ReactNode;
  unit?: string;
  icon?: ReactNode;
  tone?: 'ink' | 'go' | 'caution' | 'danger' | 'info' | 'ember';
}

const VALUE_TONE = {
  ink: 'text-ink',
  go: 'text-go',
  caution: 'text-caution',
  danger: 'text-danger',
  info: 'text-info',
  ember: 'text-ember',
};

/** Compact label/value readout used across stint + telemetry surfaces. */
export function Stat({ label, value, unit, icon, tone = 'ink' }: Props) {
  return (
    <div className="rounded-xl border border-hair bg-surface-2/60 px-3 py-2">
      <div className="flex items-center gap-1.5">
        {icon && <span className="text-faint">{icon}</span>}
        <span className="eyebrow leading-none">{label}</span>
      </div>
      <div className={`tabular mt-1.5 text-lg font-semibold leading-none ${VALUE_TONE[tone]}`}>
        {value}
        {unit && <span className="ml-0.5 text-xs font-normal text-faint">{unit}</span>}
      </div>
    </div>
  );
}
