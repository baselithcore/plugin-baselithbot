export function SegmentedControl<T extends string>(props: {
  value: T;
  onChange: (v: T) => void;
  options: { value: T; label: string }[];
  ariaLabel?: string;
}) {
  return (
    <div
      role="group"
      aria-label={props.ariaLabel}
      className="inline-flex rounded border border-bg-line bg-bg-elevated p-0.5"
    >
      {props.options.map((o) => (
        <button
          key={o.value}
          type="button"
          onClick={() => props.onChange(o.value)}
          aria-pressed={props.value === o.value}
          className={`rounded px-3 py-1.5 font-display text-xs transition ${
            props.value === o.value
              ? 'bg-accent-neon/15 text-accent-neon'
              : 'text-text-muted hover:text-text-primary'
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}
