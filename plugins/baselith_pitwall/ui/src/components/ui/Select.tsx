import { ChevronDown } from 'lucide-react';
import type { ReactNode } from 'react';

interface Props {
  value: string;
  onChange: (value: string) => void;
  ariaLabel?: string;
  className?: string;
  children: ReactNode;
}

/** Styled wrapper over a native <select> with a custom chevron. */
export function Select({ value, onChange, ariaLabel, className = '', children }: Props) {
  return (
    <div className={`relative ${className}`}>
      <select
        aria-label={ariaLabel}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full cursor-pointer appearance-none rounded-lg border border-hair bg-surface-2 py-1.5 pl-3 pr-8 text-sm text-ink outline-none transition hover:border-hair-strong focus:border-info/60"
      >
        {children}
      </select>
      <ChevronDown
        size={14}
        className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-faint"
      />
    </div>
  );
}
