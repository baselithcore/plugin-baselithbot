import {
  addEdge,
  applyEdgeChanges,
  applyNodeChanges,
  type Connection,
  type Edge,
  type EdgeChange,
  type Node,
  type NodeChange,
} from '@xyflow/react';
import { useCallback, useState } from 'react';

import type { KpiDefinition, NodeKind, ProcessGraph, ProcessNode } from '../../api/types';
import type { ProcessPayload } from '../../api/client';

export interface EditorNodeData {
  label: string;
  kind: NodeKind;
  role: string;
  resourceId?: string | null;
  costRate?: number;
  costSecs?: number;
  costRework?: number;
  costFixed?: number;
  [key: string]: unknown;
}

export type FlowNode = Node<EditorNodeData>;

let seq = 0;
const nextId = (prefix: string) => `${prefix}-${(seq += 1)}`;

function seedFromProcess(process?: ProcessGraph): {
  nodes: FlowNode[];
  edges: Edge[];
} {
  if (!process) return { nodes: [], edges: [] };
  const nodes: FlowNode[] = process.nodes.map((n, i) => ({
    id: n.id,
    type: 'editor',
    position: { x: (i % 4) * 220, y: Math.floor(i / 4) * 130 },
    data: {
      label: n.name,
      kind: n.kind,
      role: n.role,
      resourceId: n.resource_id ?? null,
      costRate: n.cost?.labor_cost_per_hour,
      costSecs: n.cost?.avg_handling_seconds,
      costRework: n.cost?.rework_rate,
      costFixed: n.cost?.fixed_cost,
    },
  }));
  const edges: Edge[] = process.edges.map((e, i) => ({
    id: `e-${e.source}-${e.target}-${i}`,
    source: e.source,
    target: e.target,
    label: e.condition || undefined,
  }));
  return { nodes, edges };
}

/** Stateful model for the interactive process editor (canvas + KPIs + meta). */
export function useProcessEditor(initial?: ProcessGraph) {
  const seed = seedFromProcess(initial);
  const [nodes, setNodes] = useState<FlowNode[]>(seed.nodes);
  const [edges, setEdges] = useState<Edge[]>(seed.edges);
  const [id, setId] = useState(initial?.id ?? '');
  const [name, setName] = useState(initial?.name ?? '');
  const [kpis, setKpis] = useState<KpiDefinition[]>(initial?.kpis ?? []);
  const [currency, setCurrency] = useState(initial?.currency ?? 'EUR');
  const [annualVolume, setAnnualVolume] = useState<number | null>(
    initial?.annual_case_volume ?? null
  );
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const onNodesChange = useCallback(
    (changes: NodeChange[]) => setNodes((nds) => applyNodeChanges(changes, nds) as FlowNode[]),
    []
  );
  const onEdgesChange = useCallback(
    (changes: EdgeChange[]) => setEdges((eds) => applyEdgeChanges(changes, eds)),
    []
  );
  const onConnect = useCallback(
    (conn: Connection) => setEdges((eds) => addEdge({ ...conn, animated: true }, eds)),
    []
  );

  const addNode = useCallback((kind: NodeKind) => {
    const newId = nextId(kind);
    setNodes((nds) => [
      ...nds,
      {
        id: newId,
        type: 'editor',
        position: { x: 80 + nds.length * 36, y: 80 + nds.length * 28 },
        data: { label: kind === 'task' ? 'New step' : kind, kind, role: '' },
      },
    ]);
    setSelectedId(newId);
  }, []);

  const updateNode = useCallback(
    (nodeId: string, patch: Partial<EditorNodeData>) =>
      setNodes((nds) =>
        nds.map((n) => (n.id === nodeId ? { ...n, data: { ...n.data, ...patch } } : n))
      ),
    []
  );

  const deleteNode = useCallback((nodeId: string) => {
    setNodes((nds) => nds.filter((n) => n.id !== nodeId));
    setEdges((eds) => eds.filter((e) => e.source !== nodeId && e.target !== nodeId));
    setSelectedId((cur) => (cur === nodeId ? null : cur));
  }, []);

  const toPayload = useCallback((): ProcessPayload => {
    const procNodes: ProcessNode[] = nodes.map((n) => {
      const { costRate, costSecs, costRework, costFixed } = n.data;
      const hasCost =
        (costRate ?? 0) > 0 || (costSecs ?? 0) > 0 || (costRework ?? 0) > 0 || (costFixed ?? 0) > 0;
      return {
        id: n.id,
        name: n.data.label || n.id,
        kind: n.data.kind,
        role: n.data.role,
        resource_id: n.data.resourceId ?? null,
        cost: hasCost
          ? {
              labor_cost_per_hour: costRate ?? 0,
              avg_handling_seconds: costSecs ?? 0,
              rework_rate: costRework ?? 0,
              fixed_cost: costFixed ?? 0,
            }
          : null,
        metadata: {},
      };
    });
    return {
      id,
      name,
      nodes: procNodes,
      edges: edges.map((e) => ({
        source: e.source,
        target: e.target,
        condition: typeof e.label === 'string' ? e.label : '',
      })),
      kpis,
      currency,
      annual_case_volume: annualVolume,
    };
  }, [nodes, edges, id, name, kpis, currency, annualVolume]);

  return {
    nodes,
    edges,
    id,
    name,
    kpis,
    currency,
    annualVolume,
    selectedId,
    setId,
    setName,
    setKpis,
    setCurrency,
    setAnnualVolume,
    setSelectedId,
    onNodesChange,
    onEdgesChange,
    onConnect,
    addNode,
    updateNode,
    deleteNode,
    toPayload,
  };
}

export type ProcessEditorModel = ReturnType<typeof useProcessEditor>;
