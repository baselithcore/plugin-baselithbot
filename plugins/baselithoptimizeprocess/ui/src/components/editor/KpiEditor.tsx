import { ArrowDownRight, ArrowUpRight, Gauge, Plus, Trash2 } from 'lucide-react';
import { useState } from 'react';

import type { KpiDefinition, KpiDirection } from '../../api/types';
import { cn, slugify } from '../../lib/ui';
import { Field } from '../forms/Field';
import type { ProcessEditorModel } from './useProcessEditor';

const emptyKpi = (): KpiDefinition => ({
  id: '',
  name: '',
  unit: '',
  direction: 'minimize',
  target: null,
  description: '',
});

/** KPI list editor — one labeled card per metric, with plain-language guidance. */
export function KpiEditor({ model }: { model: ProcessEditorModel }) {
  const { kpis, setKpis } = model;
  // Indices where the user manually edited the id — stop auto-deriving for those.
  const [pinnedIds, setPinnedIds] = useState<Set<number>>(new Set());

  const update = (i: number, patch: Partial<KpiDefinition>) =>
    setKpis(kpis.map((k, idx) => (idx === i ? { ...k, ...patch } : k)));

  const rename = (i: number, name: string) =>
    setKpis(
      kpis.map((k, idx) =>
        idx === i ? { ...k, name, id: pinnedIds.has(i) ? k.id : slugify(name) } : k
      )
    );

  const pinId = (i: number, id: string) => {
    setPinnedIds((prev) => new Set(prev).add(i));
    update(i, { id });
  };

  return (
    <div className="glass space-y-3 p-4">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <Gauge size={15} className="text-accent-soft" aria-hidden="true" />
          <h3 className="text-sm font-semibold text-slate-100">KPIs</h3>
        </div>
        <button
          className="btn-ghost px-2.5 py-1 text-xs"
          onClick={() => setKpis([...kpis, emptyKpi()])}
        >
          <Plus size={14} aria-hidden="true" />
          Add KPI
        </button>
      </div>
      <p className="text-[11px] leading-snug text-slate-500">
        The measurable outcomes that grade this process. Each KPI with a target powers breach
        alerts, bottleneck detection and forecasts.
      </p>

      {kpis.length === 0 ? (
        <p className="rounded-lg border border-dashed border-white/10 px-3 py-4 text-center text-xs text-slate-500">
          No KPIs yet — add one to start measuring this process.
        </p>
      ) : (
        kpis.map((k, i) => (
          <div
            key={i}
            className="space-y-2.5 rounded-lg border border-white/[0.08] bg-white/[0.02] p-3"
          >
            <div className="flex items-start gap-2">
              <Field
                label="Name"
                required
                hint="What you measure, e.g. “Order cycle time”."
                className="min-w-0 flex-1"
              >
                <input
                  className="field"
                  autoComplete="off"
                  placeholder="Order cycle time"
                  value={k.name}
                  onChange={(e) => rename(i, e.target.value)}
                />
              </Field>
              <button
                className="btn-icon mt-6 h-9 w-9 text-slate-500 hover:text-sev-critical"
                aria-label={`Remove KPI ${k.name || i + 1}`}
                onClick={() => setKpis(kpis.filter((_, idx) => idx !== i))}
              >
                <Trash2 size={15} aria-hidden="true" />
              </button>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <Field label="Unit" hint="e.g. hours, %, €">
                <input
                  className="field"
                  autoComplete="off"
                  placeholder="hours"
                  value={k.unit}
                  onChange={(e) => update(i, { unit: e.target.value })}
                />
              </Field>
              <Field label="Target" hint="Alert threshold to stay within.">
                <input
                  className="field"
                  type="number"
                  inputMode="decimal"
                  autoComplete="off"
                  placeholder="optional"
                  value={k.target ?? ''}
                  onChange={(e) =>
                    update(i, { target: e.target.value === '' ? null : Number(e.target.value) })
                  }
                />
              </Field>
            </div>

            <Field label="Goal" hint="Which direction counts as healthy.">
              <div className="grid grid-cols-2 gap-1.5">
                <DirButton
                  active={k.direction === 'minimize'}
                  icon={ArrowDownRight}
                  label="Lower is better"
                  onClick={() => update(i, { direction: 'minimize' as KpiDirection })}
                />
                <DirButton
                  active={k.direction === 'maximize'}
                  icon={ArrowUpRight}
                  label="Higher is better"
                  onClick={() => update(i, { direction: 'maximize' as KpiDirection })}
                />
              </div>
            </Field>

            <Field label="Identifier" hint="Auto-generated from the name; used by the API.">
              <input
                className="field font-mono text-xs"
                autoComplete="off"
                spellCheck={false}
                placeholder="order-cycle-time"
                value={k.id}
                onChange={(e) => pinId(i, slugify(e.target.value))}
              />
            </Field>
          </div>
        ))
      )}
    </div>
  );
}

function DirButton({
  active,
  icon: Icon,
  label,
  onClick,
}: {
  active: boolean;
  icon: typeof ArrowUpRight;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        'flex items-center justify-center gap-1.5 rounded-lg border px-2 py-2 text-xs font-medium transition-colors',
        active
          ? 'border-accent/40 bg-accent/[0.1] text-accent-soft'
          : 'border-white/10 bg-white/[0.02] text-slate-400 hover:border-white/20 hover:text-slate-200'
      )}
    >
      <Icon size={14} aria-hidden="true" />
      {label}
    </button>
  );
}
