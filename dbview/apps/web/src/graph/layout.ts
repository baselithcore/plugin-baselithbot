import dagre from '@dagrejs/dagre';
import type { Edge, Node } from '@xyflow/react';
import type { TableNode as TableNodeData } from '@dbview/shared';

const NODE_WIDTH = 280;
const ROW_HEIGHT = 28;
const HEADER_HEIGHT = 44;
// Vertical padding budget per node in dagre's bounding box. Without it dagre
// packs ranks too tight and column-level FK labels overlap neighboring nodes.
const NODE_VPAD = 32;

export interface LayoutResult {
  nodes: Node[];
  edges: Edge[];
}

interface LayoutEdge {
  id: string;
  source: string;
  target: string;
  sourceColumn: string;
  targetColumn: string;
}

/**
 * Cache dagre output keyed by a structural fingerprint of (tables, edges).
 * Dagre's network-simplex ranker is O(V·E) per layout; on schemas with 200+
 * tables and 500+ FKs it runs into hundreds of ms. TanStack Query refetches
 * yield a new graph object reference with identical content, which busts the
 * downstream `useMemo([graph, ...])` and recomputes the layout for no reason.
 * Module-scope LRU avoids the recompute when the schema bytes match.
 */
const LAYOUT_CACHE_MAX = 8;
const layoutCache = new Map<string, LayoutResult>();

function fingerprint(tables: TableNodeData[], fkEdges: LayoutEdge[]): string {
  const tParts: string[] = [];
  for (const t of tables) tParts.push(`${t.id}:${t.columns.length}`);
  const eParts: string[] = [];
  for (const e of fkEdges) eParts.push(`${e.id}|${e.source}>${e.target}`);
  return `${tParts.join(',')}#${eParts.join(',')}`;
}

function cloneResult(r: LayoutResult): LayoutResult {
  // React Flow mutates node.position on drag — return a fresh copy so the
  // cached entry stays pristine across renders.
  return {
    nodes: r.nodes.map((n) => ({ ...n, position: { ...n.position } })),
    edges: r.edges.map((e) => ({ ...e })),
  };
}

export function layoutSchema(tables: TableNodeData[], fkEdges: LayoutEdge[]): LayoutResult {
  const key = fingerprint(tables, fkEdges);
  const cached = layoutCache.get(key);
  if (cached) {
    layoutCache.delete(key);
    layoutCache.set(key, cached);
    return cloneResult(cached);
  }

  const g = new dagre.graphlib.Graph({ multigraph: true });
  // Wider rank/node separation + network-simplex ranker = far fewer crossings
  // and edge labels that don't collide with adjacent nodes. `tight-tree`
  // produced denser cluttered output on real-world schemas (10+ tables).
  g.setGraph({
    rankdir: 'LR',
    ranksep: 140,
    nodesep: 80,
    edgesep: 24,
    ranker: 'network-simplex',
    marginx: 32,
    marginy: 32,
  });
  g.setDefaultEdgeLabel(() => ({}));

  for (const t of tables) {
    const height = HEADER_HEIGHT + t.columns.length * ROW_HEIGHT + NODE_VPAD;
    g.setNode(t.id, { width: NODE_WIDTH, height });
  }
  for (const e of fkEdges) g.setEdge(e.source, e.target, {}, e.id);

  dagre.layout(g);

  const nodes: Node[] = tables.map((t) => {
    const pos = g.node(t.id);
    const visualHeight = HEADER_HEIGHT + t.columns.length * ROW_HEIGHT;
    return {
      id: t.id,
      type: 'table',
      dragHandle: '.dbview-drag-handle',
      position: {
        x: pos.x - NODE_WIDTH / 2,
        y: pos.y - visualHeight / 2,
      },
      data: { table: t },
      width: NODE_WIDTH,
    };
  });

  // Resolve target table display name for unambiguous edge labels.
  const tableNameById = new Map(tables.map((t) => [t.id, t.name] as const));

  const edges: Edge[] = fkEdges.map((e) => {
    const targetName = tableNameById.get(e.target) ?? e.target;
    const targetIsPkId = /^id$/i.test(e.targetColumn);
    // Short label by default: just the FK column name. The arrow + handle
    // position make the target obvious; a wide qualified label dominates the
    // canvas and overlaps with neighbours when several FKs point at the same
    // table. Full qualified form is exposed on hover via SchemaGraphView.
    const shortLabel = e.sourceColumn;
    // Long label kept on `data` so the view layer can swap it in on hover.
    // When the target column is `id` (the typical PK), drop the `.id` suffix
    // since it adds noise; otherwise keep the qualifier so `id` collisions
    // remain disambiguated.
    const longLabel = targetIsPkId
      ? `${e.sourceColumn} → ${targetName}`
      : `${e.sourceColumn} → ${targetName}.${e.targetColumn}`;
    return {
      id: e.id,
      source: e.source,
      target: e.target,
      sourceHandle: `col-${e.sourceColumn}`,
      targetHandle: `col-${e.targetColumn}`,
      type: 'smoothstep',
      animated: false,
      markerEnd: { type: 'arrowclosed' as const },
      label: shortLabel,
      data: { shortLabel, longLabel },
      labelStyle: { fontSize: 10, fill: '#a1a1aa' },
      labelBgStyle: { fill: 'rgba(17,19,25,0.85)' },
      labelBgPadding: [4, 2] as [number, number],
      labelBgBorderRadius: 4,
      style: { stroke: '#71717a', strokeWidth: 1.5 },
    };
  });

  const result: LayoutResult = { nodes, edges };
  layoutCache.set(key, result);
  if (layoutCache.size > LAYOUT_CACHE_MAX) {
    const oldest = layoutCache.keys().next().value;
    if (oldest !== undefined) layoutCache.delete(oldest);
  }
  return cloneResult(result);
}

/**
 * Drop all cached layouts. Wire to the Refresh button so a manual refresh
 * recomputes positions from scratch (e.g. after a node-size or styling change).
 */
export function clearLayoutCache(): void {
  layoutCache.clear();
}
