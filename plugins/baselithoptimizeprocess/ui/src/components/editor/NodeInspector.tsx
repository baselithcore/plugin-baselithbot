import { MousePointerClick, Trash2 } from 'lucide-react';

import type { NodeKind, Resource } from '../../api/types';
import { Field } from '../forms/Field';
import type { ProcessEditorModel } from './useProcessEditor';

const KINDS: { value: NodeKind; label: string }[] = [
  { value: 'start', label: 'Start — entry point' },
  { value: 'task', label: 'Task — a unit of work' },
  { value: 'decision', label: 'Decision — branches to one path' },
  { value: 'parallel', label: 'Parallel — splits into concurrent paths' },
  { value: 'end', label: 'End — terminal step' },
];

function numOrUndef(v: string): number | undefined {
  if (v.trim() === '') return undefined;
  const n = Number(v);
  return Number.isFinite(n) ? n : undefined;
}

/** Side panel to edit the selected canvas node, or a hint when none selected. */
export function NodeInspector({
  model,
  resources = [],
}: {
  model: ProcessEditorModel;
  resources?: Resource[];
}) {
  const node = model.nodes.find((n) => n.id === model.selectedId);
  const cur = model.currency || 'EUR';
  const assignedResource = node
    ? (resources.find((r) => r.id === node.data.resourceId) ?? null)
    : null;

  /** Assign a resource: derive its rate/role onto the step (resource = source of truth). */
  function assign(resourceId: string) {
    if (!node) return;
    if (!resourceId) {
      model.updateNode(node.id, { resourceId: null });
      return;
    }
    const resource = resources.find((r) => r.id === resourceId);
    if (!resource) return;
    model.updateNode(node.id, {
      resourceId,
      costRate: resource.cost_per_hour,
      role: resource.role || node.data.role,
    });
  }

  if (!node) {
    return (
      <div className="glass flex items-start gap-3 p-4">
        <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg bg-white/[0.05] text-slate-400">
          <MousePointerClick size={16} aria-hidden="true" />
        </span>
        <div>
          <p className="text-sm font-medium text-slate-300">No step selected</p>
          <p className="mt-1 text-xs leading-relaxed text-slate-500">
            Add a step from the palette, then click it to edit. Drag from a step’s right handle to a
            neighbour’s left handle to connect them.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="glass space-y-3 p-4">
      <h3 className="text-sm font-semibold text-slate-100">Step details</h3>

      <Field label="Step name" required hint="Shown on the map, e.g. “Pick & pack”.">
        <input
          className="field"
          autoComplete="off"
          value={node.data.label}
          onChange={(e) => model.updateNode(node.id, { label: e.target.value })}
        />
      </Field>

      <Field label="Step type" hint="How this step behaves in the flow.">
        <select
          className="field"
          value={node.data.kind}
          onChange={(e) => model.updateNode(node.id, { kind: e.target.value as NodeKind })}
        >
          {KINDS.map((k) => (
            <option key={k.value} value={k.value}>
              {k.label}
            </option>
          ))}
        </select>
      </Field>

      <Field label="Owner / team" hint="Who performs this step, e.g. “Warehouse”.">
        <input
          className="field"
          autoComplete="off"
          placeholder="Warehouse"
          value={node.data.role}
          onChange={(e) => model.updateNode(node.id, { role: e.target.value })}
        />
      </Field>

      <Field
        label="Assigned resource"
        hint="Pull rate &amp; role from a managed resource — keeps cost accurate."
      >
        <select
          className="field"
          value={node.data.resourceId ?? ''}
          onChange={(e) => assign(e.target.value)}
        >
          <option value="">— none (enter cost manually) —</option>
          {resources.map((r) => (
            <option key={r.id} value={r.id}>
              {r.name}
              {r.role ? ` · ${r.role}` : ''} — {r.cost_per_hour} {r.currency}/h
            </option>
          ))}
        </select>
      </Field>

      <div className="border-t border-white/[0.08] pt-3">
        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">
          Cost &amp; effort
        </p>
        <p className="mt-0.5 text-[11px] leading-snug text-slate-500">
          Optional — powers ROI savings and cycle-time simulation. Leave blank if unknown.
        </p>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <Field
          label="Labour cost"
          suffix={`${cur}/h`}
          hint={
            assignedResource
              ? `From “${assignedResource.name}”. Change it on the resource.`
              : 'Hourly rate of the people involved.'
          }
        >
          <input
            type="number"
            inputMode="decimal"
            min={0}
            autoComplete="off"
            className="field"
            placeholder="0"
            disabled={!!assignedResource}
            value={node.data.costRate ?? ''}
            onChange={(e) => model.updateNode(node.id, { costRate: numOrUndef(e.target.value) })}
          />
        </Field>
        <Field label="Handling time" suffix="sec" hint="Avg. seconds of work per case.">
          <input
            type="number"
            inputMode="numeric"
            min={0}
            autoComplete="off"
            className="field"
            placeholder="0"
            value={node.data.costSecs ?? ''}
            onChange={(e) => model.updateNode(node.id, { costSecs: numOrUndef(e.target.value) })}
          />
        </Field>
        <Field label="Rework rate" suffix="0–1" hint="Share of cases redone here (0.1 = 10%).">
          <input
            type="number"
            inputMode="decimal"
            min={0}
            max={1}
            step={0.05}
            autoComplete="off"
            className="field"
            placeholder="0"
            value={node.data.costRework ?? ''}
            onChange={(e) => model.updateNode(node.id, { costRework: numOrUndef(e.target.value) })}
          />
        </Field>
        <Field label="Fixed cost" suffix={cur} hint="Flat cost per case (tools, fees).">
          <input
            type="number"
            inputMode="decimal"
            min={0}
            autoComplete="off"
            className="field"
            placeholder="0"
            value={node.data.costFixed ?? ''}
            onChange={(e) => model.updateNode(node.id, { costFixed: numOrUndef(e.target.value) })}
          />
        </Field>
      </div>

      <p className="font-mono text-[10px] text-slate-600">id: {node.id}</p>
      <button
        className="btn-danger w-full justify-center"
        onClick={() => {
          if (window.confirm(`Delete step "${node.data.label}"?`)) model.deleteNode(node.id);
        }}
      >
        <Trash2 size={15} aria-hidden="true" />
        Delete step
      </button>
    </div>
  );
}
