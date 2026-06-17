import type { Edge, Node } from '@xyflow/react';

import type { Bottleneck, ProcessGraph, Severity } from '../api/types';
import { severityColor, severityRank } from './ui';

const COL_WIDTH = 240;
const ROW_HEIGHT = 96;

/** Worst bottleneck severity per node id, for tinting. */
function worstSeverityByNode(bottlenecks: Bottleneck[]): Record<string, Severity> {
  const out: Record<string, Severity> = {};
  for (const b of bottlenecks) {
    if (!b.node_id) continue;
    const current = out[b.node_id];
    if (!current || severityRank[b.severity] > severityRank[current]) {
      out[b.node_id] = b.severity;
    }
  }
  return out;
}

/**
 * Assign each node a column from its longest-path depth (layered DAG layout),
 * stacking nodes that share a depth into rows. Cycles degrade gracefully — a
 * visited guard stops infinite recursion.
 */
function computeDepths(graph: ProcessGraph): Record<string, number> {
  const outgoing: Record<string, string[]> = {};
  const indegree: Record<string, number> = {};
  for (const node of graph.nodes) {
    outgoing[node.id] = [];
    indegree[node.id] = 0;
  }
  for (const edge of graph.edges) {
    if (outgoing[edge.source] && edge.target in indegree) {
      outgoing[edge.source].push(edge.target);
      indegree[edge.target] += 1;
    }
  }

  const depth: Record<string, number> = {};
  const roots = graph.nodes.filter((n) => indegree[n.id] === 0).map((n) => n.id);
  const queue = roots.length ? [...roots] : graph.nodes.map((n) => n.id);
  for (const id of queue) depth[id] = 0;

  const seen = new Set<string>();
  while (queue.length) {
    const id = queue.shift() as string;
    if (seen.has(id)) continue;
    seen.add(id);
    for (const next of outgoing[id] ?? []) {
      depth[next] = Math.max(depth[next] ?? 0, (depth[id] ?? 0) + 1);
      queue.push(next);
    }
  }
  return depth;
}

export function buildFlow(
  graph: ProcessGraph,
  bottlenecks: Bottleneck[]
): { nodes: Node[]; edges: Edge[] } {
  const depth = computeDepths(graph);
  const severity = worstSeverityByNode(bottlenecks);
  const rowCursor: Record<number, number> = {};

  const nodes: Node[] = graph.nodes.map((node) => {
    const col = depth[node.id] ?? 0;
    const row = rowCursor[col] ?? 0;
    rowCursor[col] = row + 1;
    const sev = severity[node.id];
    const accent = sev ? severityColor[sev] : '#38bdf8';
    return {
      id: node.id,
      position: { x: col * COL_WIDTH, y: row * ROW_HEIGHT },
      data: { label: node.name, kind: node.kind, severity: sev },
      type: 'process',
      style: { '--node-accent': accent } as Record<string, string>,
    };
  });

  const edges: Edge[] = graph.edges.map((edge, i) => ({
    id: `e-${edge.source}-${edge.target}-${i}`,
    source: edge.source,
    target: edge.target,
    label: edge.condition || undefined,
    animated: true,
    style: { stroke: 'rgba(148,163,184,0.45)' },
    labelStyle: { fill: '#94a3b8', fontSize: 11 },
  }));

  return { nodes, edges };
}
