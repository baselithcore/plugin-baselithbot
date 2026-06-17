import {
  Background,
  BackgroundVariant,
  Controls,
  ReactFlow,
  ReactFlowProvider,
} from '@xyflow/react';
import type { LucideIcon } from 'lucide-react';
import { Flag, GitFork, Play, Rows3, Square } from 'lucide-react';
import { useEffect, useState } from 'react';

import { api } from '../../api/client';
import type { NodeKind, ProcessGraph, Resource, SimulationComparison } from '../../api/types';
import { slugify } from '../../lib/ui';
import { Field } from '../forms/Field';
import { EditorNode } from './EditorNode';
import { KpiEditor } from './KpiEditor';
import { NodeInspector } from './NodeInspector';
import { useProcessEditor } from './useProcessEditor';

const nodeTypes = { editor: EditorNode };

const PALETTE: { kind: NodeKind; label: string; icon: LucideIcon }[] = [
  { kind: 'start', label: 'Start', icon: Play },
  { kind: 'task', label: 'Task', icon: Square },
  { kind: 'decision', label: 'Decision', icon: GitFork },
  { kind: 'parallel', label: 'Parallel', icon: Rows3 },
  { kind: 'end', label: 'End', icon: Flag },
];

interface ProcessEditorProps {
  initial?: ProcessGraph;
  onSaved: (process: ProcessGraph) => void;
  onCancel?: () => void;
}

function EditorInner({ initial, onSaved, onCancel }: ProcessEditorProps) {
  const model = useProcessEditor(initial);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [sim, setSim] = useState<SimulationComparison | null>(null);
  const [simBusy, setSimBusy] = useState(false);
  const [resources, setResources] = useState<Resource[]>([]);
  // Auto-derive the id from the name until the user edits it directly.
  const [idEdited, setIdEdited] = useState(!!initial);

  useEffect(() => {
    void api
      .listResources()
      .then((list) => setResources(list.filter((r) => r.active)))
      .catch(() => setResources([]));
  }, []);

  function onNameChange(value: string) {
    model.setName(value);
    if (!idEdited && !initial) model.setId(slugify(value));
  }

  async function runSimulation() {
    if (!initial) return;
    setSimBusy(true);
    setError(null);
    try {
      setSim(await api.simulateVariant(initial.id, model.toPayload()));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Simulation failed');
    } finally {
      setSimBusy(false);
    }
  }

  async function applyAsChange() {
    if (!initial) return;
    setBusy(true);
    setError(null);
    try {
      await api.applyChange(initial.id, model.toPayload());
      onSaved(await api.getProcess(initial.id));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Apply failed');
    } finally {
      setBusy(false);
    }
  }

  async function save() {
    setError(null);
    if (!model.name) {
      setError('Give the process a name before saving.');
      return;
    }
    if (!model.id) {
      setError('An identifier is required — type a name to generate one.');
      return;
    }
    if (model.nodes.length === 0) {
      setError('Add at least one step from the palette on the left.');
      return;
    }
    setBusy(true);
    try {
      onSaved(await api.registerProcess(model.toPayload()));
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Save failed');
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      <header className="border-b border-white/10 bg-neutral-950/35 px-5 py-4">
        <div className="flex flex-wrap items-start gap-3">
          <Field
            label="Process name"
            required
            hint="A clear business name, e.g. “Order Fulfillment”."
            className="min-w-[16rem] flex-1"
          >
            <input
              className="field"
              name="process-name"
              autoComplete="off"
              placeholder="Order Fulfillment"
              value={model.name}
              onChange={(e) => onNameChange(e.target.value)}
            />
          </Field>
          <Field
            label="Identifier"
            hint={initial ? 'Fixed after creation.' : 'Auto-filled from the name.'}
            className="w-48"
          >
            <input
              className="field font-mono text-xs"
              name="process-id"
              autoComplete="off"
              spellCheck={false}
              placeholder="order-fulfillment"
              value={model.id}
              onChange={(e) => {
                setIdEdited(true);
                model.setId(slugify(e.target.value));
              }}
              disabled={!!initial}
            />
          </Field>
          <Field label="Currency" hint="For cost rollups." className="w-24">
            <input
              className="field"
              name="process-currency"
              autoComplete="off"
              spellCheck={false}
              placeholder="EUR"
              value={model.currency}
              onChange={(e) => model.setCurrency(e.target.value.toUpperCase())}
            />
          </Field>
          <Field label="Cases / year" hint="Scales cost to annual." className="w-36">
            <input
              className="field"
              name="annual-case-volume"
              type="number"
              inputMode="numeric"
              min={0}
              autoComplete="off"
              placeholder="12000"
              value={model.annualVolume ?? ''}
              onChange={(e) =>
                model.setAnnualVolume(e.target.value === '' ? null : Number(e.target.value))
              }
            />
          </Field>
          <div className="ml-auto flex flex-wrap items-center gap-2 self-end">
            {initial && (
              <button className="btn-ghost" onClick={runSimulation} disabled={simBusy}>
                {simBusy ? 'Simulating…' : 'Simulate vs Saved'}
              </button>
            )}
            {initial && (
              <button className="btn-ghost" onClick={applyAsChange} disabled={busy}>
                Apply as Change
              </button>
            )}
            {onCancel && (
              <button className="btn-ghost" onClick={onCancel}>
                Cancel
              </button>
            )}
            <button className="btn-primary" onClick={save} disabled={busy}>
              {busy ? 'Saving…' : initial ? 'Save Changes' : 'Create Process'}
            </button>
          </div>
        </div>
      </header>

      {sim && <SimulationBanner sim={sim} onClose={() => setSim(null)} />}

      {error && (
        <p className="border-b border-sev-critical/20 bg-sev-critical/10 px-5 py-2 text-sm text-sev-critical">
          {error}
        </p>
      )}

      <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
        <aside className="flex shrink-0 flex-col gap-2 border-b border-white/10 bg-neutral-950/30 p-3 lg:w-44 lg:border-b-0 lg:border-r">
          <p className="section-title px-1">Add a step</p>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-5 lg:grid-cols-1">
            {PALETTE.map((p) => (
              <button
                key={p.kind}
                className="btn-ghost justify-start text-sm"
                onClick={() => model.addNode(p.kind)}
              >
                <p.icon size={15} aria-hidden="true" />
                {p.label}
              </button>
            ))}
          </div>
          <p className="mt-1 px-1 text-[10px] leading-relaxed text-slate-600 lg:mt-2">
            Tip: drag from a step’s right handle to another step’s left handle to link them.
          </p>
        </aside>

        <div className="h-[22rem] min-w-0 flex-1 bg-neutral-950/20 lg:h-full">
          <ReactFlow
            nodes={model.nodes}
            edges={model.edges}
            nodeTypes={nodeTypes}
            onNodesChange={model.onNodesChange}
            onEdgesChange={model.onEdgesChange}
            onConnect={model.onConnect}
            onNodeClick={(_, n) => model.setSelectedId(n.id)}
            onPaneClick={() => model.setSelectedId(null)}
            proOptions={{ hideAttribution: true }}
            deleteKeyCode={['Backspace', 'Delete']}
            fitView
            minZoom={0.2}
            maxZoom={1.5}
          >
            <Background
              variant={BackgroundVariant.Dots}
              gap={24}
              size={1}
              color="rgba(148,163,184,0.16)"
            />
            <Controls showInteractive={false} />
          </ReactFlow>
        </div>

        <aside className="max-h-72 shrink-0 space-y-3 overflow-y-auto border-t border-white/10 bg-neutral-950/30 p-3 lg:max-h-none lg:w-80 lg:border-l lg:border-t-0">
          <NodeInspector model={model} resources={resources} />
          <KpiEditor model={model} />
        </aside>
      </div>
    </div>
  );
}

function fmtSecs(s: number): string {
  const a = Math.abs(s);
  if (a >= 3600) return `${(s / 3600).toFixed(1)} h`;
  if (a >= 60) return `${(s / 60).toFixed(1)} min`;
  return `${s.toFixed(0)} s`;
}

function Delta({
  label,
  value,
  pct,
  suffix = '',
}: {
  label: string;
  value: string;
  pct?: number;
  suffix?: string;
}) {
  // Negative delta = improvement (faster / cheaper) → green.
  const improved = pct !== undefined ? pct < 0 : value.trim().startsWith('-');
  return (
    <div>
      <p className="text-[11px] uppercase tracking-wide text-slate-500">{label}</p>
      <p
        className={
          improved
            ? 'font-mono text-sm font-semibold text-sev-low'
            : 'font-mono text-sm font-semibold text-sev-medium'
        }
      >
        {value}
        {suffix}
        {pct !== undefined && <span className="ml-1 text-[11px] font-normal">({pct}%)</span>}
      </p>
    </div>
  );
}

/** What-if result banner comparing the draft against the saved baseline. */
function SimulationBanner({ sim, onClose }: { sim: SimulationComparison; onClose: () => void }) {
  return (
    <div className="flex flex-wrap items-center gap-x-6 gap-y-2 border-b border-accent/20 bg-accent/5 px-5 py-3">
      <span className="text-xs font-semibold uppercase tracking-wide text-accent-soft">
        What-if vs saved
      </span>
      <Delta
        label="Cycle time Δ"
        value={fmtSecs(sim.cycle_time_delta_seconds)}
        pct={sim.cycle_time_pct}
      />
      <Delta
        label="Cost / case Δ"
        value={`${sim.cost_per_case_delta.toLocaleString()} ${sim.variant.currency}`}
        pct={sim.cost_pct}
      />
      {sim.annual_cost_delta !== null && (
        <Delta
          label="Annual Δ"
          value={`${sim.annual_cost_delta.toLocaleString()} ${sim.variant.currency}`}
        />
      )}
      <button className="btn-ghost ml-auto text-xs" onClick={onClose}>
        Dismiss
      </button>
    </div>
  );
}

/** Visual drag-and-drop process editor (React Flow), wrapped in its provider. */
export function ProcessEditor(props: ProcessEditorProps) {
  return (
    <ReactFlowProvider>
      <EditorInner {...props} />
    </ReactFlowProvider>
  );
}
