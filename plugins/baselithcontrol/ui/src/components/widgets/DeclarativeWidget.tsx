import { useEffect, useState } from 'react';
import { fetchWidgetData } from '@/lib/api';
import { formatValue, getByPath, highlightTone, type Tone } from '@/lib/format';
import type { WidgetSpec } from '@/types';
import { MetricChip } from './MetricChip';

// The zero-code escape hatch: render any plugin's JSON status endpoint from a
// manifest-declared spec, with no plugin-specific frontend code. Single generic
// renderer over the normalized field mappings (Homepage `customapi` pattern).
export function DeclarativeWidget({ spec }: { spec: WidgetSpec }) {
  const [data, setData] = useState<unknown>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    fetchWidgetData(spec.endpoint)
      .then((d) => alive && setData(d))
      .catch((e) => alive && setError(e instanceof Error ? e.message : 'failed'));
    return () => {
      alive = false;
    };
  }, [spec.endpoint]);

  if (error) {
    return (
      <p className="text-[13px] text-rose-500">
        {spec.title}: {error}
      </p>
    );
  }

  const rows = spec.fields.map((f) => {
    const raw = getByPath(data, f.path);
    return {
      label: f.label ?? f.path,
      value: formatValue(raw, f.format),
      tone: highlightTone(raw, f.highlight) as Tone,
    };
  });

  return (
    <div className="glass flex flex-col gap-2 p-4">
      <h4 className="text-[13px] font-semibold t-primary">{spec.title}</h4>
      <div
        className={spec.display === 'block' ? 'grid grid-cols-2 gap-2' : 'flex flex-col gap-1.5'}
      >
        {rows.map((r, i) => (
          <MetricChip key={i} label={r.label} value={r.value} tone={r.tone} />
        ))}
      </div>
    </div>
  );
}
