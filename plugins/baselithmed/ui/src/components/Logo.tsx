interface Props {
  className?: string;
  compact?: boolean;
}

export function Logo({ className = '', compact = false }: Props) {
  return (
    <div className={`flex items-center gap-3 ${className}`}>
      <span
        aria-hidden
        className="relative grid h-10 w-10 place-items-center rounded-xl bg-gradient-to-br from-accent-600 to-accent-800 text-white shadow-e2"
      >
        <span className="absolute inset-0 rounded-xl bg-white/10 mix-blend-overlay" />
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="1.75"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="relative h-5 w-5"
        >
          <path d="M12 21s-7-4.35-7-10a5 5 0 0 1 9-3 5 5 0 0 1 9 3c0 5.65-7 10-7 10z" />
          <path d="M8 12h3l1-2.4L14 14l1-2h2" />
        </svg>
      </span>
      {!compact && (
        <div className="leading-tight">
          <div className="font-display text-base font-semibold tracking-tight">BaselithMed</div>
          <div className="text-2xs font-medium uppercase tracking-[0.18em] text-ink-400">
            Pre-Triage Clinico
          </div>
        </div>
      )}
    </div>
  );
}
