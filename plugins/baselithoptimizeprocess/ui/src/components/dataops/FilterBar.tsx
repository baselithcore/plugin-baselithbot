import { Filter, X } from 'lucide-react';
import { useState } from 'react';

import type { EventFilter } from '../../api/types';
import { cn } from '../../lib/ui';

interface FilterBarProps {
  onApply: (filter: EventFilter) => void;
  activities?: string[];
  resources?: string[];
}

const EMPTY: EventFilter = {};

/** Celonis-style case segmentation bar, reused across the analysis panels. */
export function FilterBar({ onApply, activities = [], resources = [] }: FilterBarProps) {
  const [draft, setDraft] = useState<EventFilter>(EMPTY);
  const [open, setOpen] = useState(false);

  const active = Object.values(draft).some((v) => v !== undefined && v !== '');

  function set<K extends keyof EventFilter>(key: K, value: EventFilter[K]) {
    setDraft((d) => ({ ...d, [key]: value || undefined }));
  }

  function clear() {
    setDraft(EMPTY);
    onApply(EMPTY);
  }

  return (
    <div className="glass p-3">
      <div className="flex items-center justify-between">
        <button
          className="flex items-center gap-1.5 text-xs font-medium text-slate-300"
          onClick={() => setOpen((o) => !o)}
        >
          <Filter size={14} aria-hidden="true" />
          Filter cases
          {active && <span className="chip bg-accent/15 text-accent-soft">active</span>}
        </button>
        {active && (
          <button className="flex items-center gap-1 text-[11px] text-slate-500" onClick={clear}>
            <X size={12} aria-hidden="true" /> Clear
          </button>
        )}
      </div>

      {open && (
        <div className="mt-3 flex flex-wrap items-end gap-2">
          <Picker
            label="Activity"
            value={draft.activity ?? ''}
            options={activities}
            onChange={(v) => set('activity', v)}
          />
          <Picker
            label="Resource"
            value={draft.resource ?? ''}
            options={resources}
            onChange={(v) => set('resource', v)}
          />
          <Num
            label="Min dur (s)"
            value={draft.min_duration_seconds}
            onChange={(v) => set('min_duration_seconds', v)}
          />
          <Num
            label="Max dur (s)"
            value={draft.max_duration_seconds}
            onChange={(v) => set('max_duration_seconds', v)}
          />
          <button className="btn-primary" onClick={() => onApply(draft)}>
            Apply
          </button>
        </div>
      )}
    </div>
  );
}

function Picker({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (v: string) => void;
}) {
  const fieldName = `filter-${label.toLowerCase().replace(/\s+/g, '-')}`;
  return (
    <label className={cn('text-[11px] text-slate-400')}>
      {label}
      {options.length > 0 ? (
        <select
          className="field mt-1 w-40"
          name={fieldName}
          value={value}
          onChange={(e) => onChange(e.target.value)}
        >
          <option value="">Any</option>
          {options.map((o) => (
            <option key={o} value={o}>
              {o}
            </option>
          ))}
        </select>
      ) : (
        <input
          className="field mt-1 w-40"
          name={fieldName}
          autoComplete="off"
          spellCheck={false}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="Any…"
        />
      )}
    </label>
  );
}

function Num({
  label,
  value,
  onChange,
}: {
  label: string;
  value: number | undefined;
  onChange: (v: number | undefined) => void;
}) {
  const fieldName = `filter-${label.toLowerCase().replace(/[^a-z]+/g, '-')}`;
  return (
    <label className="text-[11px] text-slate-400">
      {label}
      <input
        className="field mt-1 w-28"
        type="number"
        inputMode="numeric"
        name={fieldName}
        autoComplete="off"
        min={0}
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value ? Number(e.target.value) : undefined)}
        placeholder="—"
      />
    </label>
  );
}
