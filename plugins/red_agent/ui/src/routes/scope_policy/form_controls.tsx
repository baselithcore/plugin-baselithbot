export function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-text-muted">{label}</dt>
      <dd className="font-mono text-text-primary">{value}</dd>
    </div>
  );
}

export function NumberRow({
  label,
  value,
  min,
  max,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  onChange: (v: number) => void;
}) {
  return (
    <div className="flex items-center justify-between gap-3">
      <dt className="text-text-muted">{label}</dt>
      <dd>
        <input
          type="number"
          min={min}
          max={max}
          value={value}
          onChange={(e) => onChange(parseInt(e.target.value, 10) || min)}
          className="ra-input h-8 w-24 text-right font-mono"
        />
      </dd>
    </div>
  );
}

export function NumberInput({
  label,
  value,
  min,
  max,
  step,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  onChange: (v: number) => void;
}) {
  return (
    <div>
      <label className="mb-1.5 block text-2xs font-mono uppercase tracking-wider text-text-muted">
        {label}
      </label>
      <input
        type="number"
        min={min}
        max={max}
        step={step ?? 1}
        value={value}
        onChange={(e) => {
          const parsed =
            step && step < 1 ? parseFloat(e.target.value) : parseInt(e.target.value, 10);
          onChange(Number.isFinite(parsed) ? parsed : min);
        }}
        className="ra-input"
      />
    </div>
  );
}

export function SelectInput<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: { value: T; label: string }[];
  onChange: (v: T) => void;
}) {
  return (
    <div>
      <label className="mb-1.5 block text-2xs font-mono uppercase tracking-wider text-text-muted">
        {label}
      </label>
      <select value={value} onChange={(e) => onChange(e.target.value as T)} className="ra-select">
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}

export function ToggleRow({
  label,
  description,
  checked,
  onChange,
  tone,
}: {
  label: string;
  description: string;
  checked: boolean;
  onChange: (v: boolean) => void;
  tone?: 'danger';
}) {
  return (
    <label
      className={`flex cursor-pointer items-start justify-between gap-3 rounded-md border bg-bg-elevated px-3 py-3 transition-colors ${
        checked
          ? tone === 'danger'
            ? 'border-sev-critical/40 bg-sev-critical/5'
            : 'border-brand/50'
          : 'border-bg-line hover:border-bg-line-strong'
      }`}
    >
      <div className="min-w-0">
        <div className="font-display text-sm font-medium text-text-primary">{label}</div>
        <p className="mt-0.5 text-xs text-text-muted">{description}</p>
      </div>
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="mt-1 accent-brand"
      />
    </label>
  );
}
